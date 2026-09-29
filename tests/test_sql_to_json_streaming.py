"""MOD-OPS-17 regression tests for the streaming SQL-to-JSON converter.

`scripts/sql_to_json.py` used to read the entire dump into a string and then
accumulate every logical statement into a list, so peak memory was a multiple
of the input size. A mature instance dump is routinely hundreds of MB, and the
Oracle Free Tier hosts iqoqo targets have 1 GB of RAM, so conversion could OOM
regardless of how small the resulting JSON was.

These tests pin the streaming contract and, critically, that the refactor did
not change a single byte of the output.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.sql_to_json import (
    _iter_statements_from_lines,
    convert_sql_dump,
    iter_parsed_rows,
    iter_sql_statements,
    parse_sql_dump,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

MULTILINE_DUMP = """
-- Test SQL dump
INSERT INTO "iqoqo"."manifestation" (id, isbn, title, authors, meta, added) VALUES
('1', '9780451524935', 'Test Book', 'Test Author', '{"key": "value"}', '2024-01-01 12:00:00'),
('2', '9781234567890', 'Another Book', 'Another Author', '{}', '2024-01-02 12:00:00');
INSERT INTO "iqoqo"."item" (id, manifestation_id, added_by, added_at, meta) VALUES
('1', '1', '7', '2024-01-01 12:00:00', '{}');
INSERT INTO "iqoqo"."client" (id, address, user, added) VALUES
('1', '192.168.1.1', '*', '2024-01-01 12:00:00');
"""


@pytest.fixture()
def dump_file(tmp_path: Path) -> Path:
    path = tmp_path / "dump.sql"
    path.write_text(MULTILINE_DUMP, encoding="utf-8")
    return path


# ── Output equivalence ──────────────────────────────────────────────


def test_streaming_output_matches_in_memory_parser(dump_file: Path, tmp_path: Path) -> None:
    """The streaming converter must produce exactly what parse_sql_dump did."""
    out = tmp_path / "out.json"
    counts = convert_sql_dump(dump_file, out)

    streamed = json.loads(out.read_text(encoding="utf-8"))
    in_memory = parse_sql_dump(dump_file.read_text(encoding="utf-8"))

    assert streamed == in_memory
    assert counts == {"clients": 1, "manifestations": 2, "items": 1}


def test_streaming_output_is_valid_json_with_all_keys(dump_file: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    convert_sql_dump(dump_file, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data) == {"clients", "manifestations", "items"}
    assert data["manifestations"][0]["title"] == "Test Book"
    assert data["manifestations"][0]["meta"] == {"key": "value"}


def test_empty_collections_are_still_present(tmp_path: Path) -> None:
    """A dump with no rows must still produce all three keys, for downstream consumers."""
    dump = tmp_path / "empty.sql"
    dump.write_text("-- nothing here\n", encoding="utf-8")
    out = tmp_path / "out.json"
    counts = convert_sql_dump(dump, out)
    assert counts == {"clients": 0, "manifestations": 0, "items": 0}
    assert json.loads(out.read_text(encoding="utf-8")) == {"clients": [], "manifestations": [], "items": []}


def test_interleaved_tables_are_grouped_correctly(tmp_path: Path) -> None:
    """Records must land in the right collection even when tables interleave."""
    dump = tmp_path / "interleaved.sql"
    dump.write_text(
        'INSERT INTO "iqoqo"."item" (id, manifestation_id, added_by, added_at, meta) VALUES (1, 1, 7, 2024, \'{}\');\n'
        'INSERT INTO "iqoqo"."manifestation" (id, isbn, title, authors, meta, added) VALUES (1, 978, T, A, \'{}\', 2024);\n'
        'INSERT INTO "iqoqo"."item" (id, manifestation_id, added_by, added_at, meta) VALUES (2, 1, 7, 2024, \'{}\');\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    convert_sql_dump(dump, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["items"]) == 2
    assert len(data["manifestations"]) == 1


# ── Streaming contract ──────────────────────────────────────────────


def test_iter_sql_statements_is_a_generator_not_a_list(dump_file: Path) -> None:
    """iter_sql_statements must be lazy; building a list is the regression."""
    import inspect

    assert inspect.isgeneratorfunction(iter_sql_statements)
    assert inspect.isgeneratorfunction(_iter_statements_from_lines)


def test_iter_sql_statements_yields_one_statement_at_a_time(dump_file: Path) -> None:
    statements = list(iter_sql_statements(dump_file))
    assert len(statements) == 3
    for statement in statements:
        assert statement.startswith("INSERT INTO")
        # The multi-line join must have produced single-line statements.
        assert "\n" not in statement


def test_multiline_statements_are_joined() -> None:
    """pg_dump splits VALUES across lines; they must be rejoined before matching."""
    lines = [
        'INSERT INTO "iqoqo"."item" (id, manifestation_id, added_by, added_at, meta) VALUES',
        "(1, 1, 7, 2024, '{}'),",
        "(2, 1, 7, 2024, '{}');",
    ]
    statements = list(_iter_statements_from_lines(iter(lines)))
    assert len(statements) == 1
    rows = list(iter_parsed_rows(statements[0]))
    assert len(rows) == 2


def test_trailing_statement_without_semicolon_is_still_emitted() -> None:
    """A truncated dump's last statement must not be silently discarded."""
    lines = ['INSERT INTO "iqoqo"."item" (id, manifestation_id, added_by, added_at, meta) VALUES (1, 1, 7, 2024, \'{}\')']
    statements = list(_iter_statements_from_lines(iter(lines)))
    assert len(statements) == 1
    assert len(list(iter_parsed_rows(statements[0]))) == 1


def test_comment_lines_are_skipped() -> None:
    lines = [
        "-- a leading comment",
        'INSERT INTO "iqoqo"."client" (id, address, user, added) VALUES (1, a, b, c);',
        "-- a trailing comment",
    ]
    statements = list(_iter_statements_from_lines(iter(lines)))
    assert len(statements) == 1
    assert "comment" not in statements[0]


# ── Durability ──────────────────────────────────────────────────────


def test_no_partial_file_survives_a_failure(tmp_path: Path) -> None:
    """An error must not leave a .partial or spool file behind to be mistaken for output."""
    dump = tmp_path / "dump.sql"
    dump.write_text(
        'INSERT INTO "iqoqo"."client" (id, address, user, added) VALUES (1, a, b, c);\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    def boom(_statement):
        raise RuntimeError("simulated parse failure")

    import scripts.sql_to_json as mod

    original = mod.iter_sql_statements
    mod.iter_sql_statements = boom
    try:
        with pytest.raises(RuntimeError, match="simulated parse failure"):
            convert_sql_dump(dump, out)
    finally:
        mod.iter_sql_statements = original

    assert not out.exists()
    assert not out.with_name(out.name + ".partial").exists()
    # No spool files leaked into the temp dir.
    assert list(tmp_path.glob("sql2json_*")) == []


def test_existing_output_is_not_clobbered_on_failure(tmp_path: Path) -> None:
    """A pre-existing conversion must survive a failed re-run intact."""
    out = tmp_path / "out.json"
    out.write_text('{"clients": [], "manifestations": [], "items": []}', encoding="utf-8")

    import scripts.sql_to_json as mod

    original = mod.iter_sql_statements
    mod.iter_sql_statements = lambda _p: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        with pytest.raises(RuntimeError):
            convert_sql_dump(tmp_path / "missing.sql", out)
    finally:
        mod.iter_sql_statements = original

    assert json.loads(out.read_text(encoding="utf-8")) == {"clients": [], "manifestations": [], "items": []}


# ── Bounded memory, measured in a child process ──────────────────────


@pytest.mark.slow
def test_peak_memory_is_bounded_independently_of_dump_size(tmp_path: Path) -> None:
    """The regression this guards is a memory *scaling* property, so it is
    measured rather than asserted structurally.

    Two dumps of very different sizes are converted in separate child
    processes and their peak RSS compared. If the converter buffered the dump,
    peak RSS would grow roughly in proportion to input size; with streaming it
    stays near the interpreter's own baseline.
    """
    small = tmp_path / "small.sql"
    large = tmp_path / "large.sql"
    for path, rows in ((small, 200), (large, 60_000)):
        with open(path, "w", encoding="utf-8") as f:
            f.write('INSERT INTO "iqoqo"."item" (id, manifestation_id, added_by, added_at, meta) VALUES\n')
            f.write(",\n".join(f"('{i}', '{i}', '7', '2024-01-01 00:00:00', '{{}}')" for i in range(1, rows + 1)) + ";\n")

    def peak_mib(dump: Path, out: Path) -> float:
        code = (
            "import resource,sys;"
            f"sys.path.insert(0, {str(REPO_ROOT)!r});"
            "from pathlib import Path;"
            "from scripts.sql_to_json import convert_sql_dump;"
            "convert_sql_dump(Path(sys.argv[1]),Path(sys.argv[2]));"
            "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)"
        )
        result = subprocess.run([sys.executable, "-c", code, str(dump), str(out)], capture_output=True, text=True, check=True)
        return int(result.stdout.strip()) / 1024

    small_peak = peak_mib(small, tmp_path / "small.json")
    large_peak = peak_mib(large, tmp_path / "large.json")

    size_growth = (large.stat().st_size - small.stat().st_size) / 1024 / 1024
    memory_growth = large_peak - small_peak

    # The dumps differ by several MiB. A buffering implementation would show
    # peak RSS growing by at least that much.
    assert size_growth > 3.0, f"test dumps are too similar to be meaningful ({size_growth:.2f} MiB apart)"
    assert memory_growth < size_growth * 0.25, (
        f"peak RSS grew {memory_growth:.1f} MiB while the input grew {size_growth:.1f} MiB — the converter is still buffering the dump"
    )
