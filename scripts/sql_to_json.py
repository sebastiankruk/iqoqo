"""
Convert legacy SQL dump to JSON format for migration.

This script parses the legacy iqoqo SQL dump and converts it to a JSON format
that can be used by the migrate_legacy.py script.

Usage:
    python scripts/sql_to_json.py <input.sql> <output.json>
"""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#

import argparse
import json
import re
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# MOD-OPS-17: cap on how many physical lines may be joined into one logical
# INSERT statement before the buffer is flushed. A well-formed pg_dump line
# ends each statement within a handful of lines, so this only ever triggers on
# a malformed or truncated dump — where it bounds memory instead of letting the
# buffer grow without limit. Generous enough not to interfere with a statement
# whose rows legitimately span many lines.
MAX_STATEMENT_LINES = 100_000

# Matches a single logical INSERT statement, with or without a schema qualifier
# and with or without an explicit column list. Compiled once at module scope:
# the streaming path matches every statement in the dump, and re-compiling per
# statement was measurable on multi-hundred-thousand-row dumps.
#
# Supports both pg_dump output styles:
#   INSERT INTO "iqoqo"."item" (id, …) VALUES (…), (…);
#   INSERT INTO iqoqo.item VALUES (…);
INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+"
    r'(?:"?iqoqo"?\.)"?(\w+)"?'  # schema + table name (group 1)
    r"(?:\s*\([^)]*\))?\s*VALUES\s+"  # optional column list + VALUES keyword
    r"(.+?)\s*;?\s*$",  # values block (group 2)
    re.IGNORECASE,
)

# Table name in a pg_dump INSERT -> output collection key.
COLLECTION_FOR_TABLE = {
    "client": "clients",
    "manifestation": "manifestations",
    "item": "items",
}


def _parse_sql_values(values_str: str) -> list[str | None]:
    """
    Parse a comma-separated PostgreSQL VALUES string into a list of Python values.

    Handles SQL single-quoted strings (with ``''`` as escaped single quote) and
    unquoted NULL literals.

    Args:
        values_str: The raw content between the outer parentheses of VALUES (...).

    Returns:
        List of string values (or None for SQL NULL).
    """
    result: list[str | None] = []
    current: list[str] = []
    in_quote = False
    i = 0

    while i < len(values_str):
        ch = values_str[i]
        if in_quote:
            if ch == "'" and i + 1 < len(values_str) and values_str[i + 1] == "'":
                # SQL-escaped single quote: '' → '
                current.append("'")
                i += 2
                continue

            if ch == "'":
                # End of quoted string
                in_quote = False
            else:
                current.append(ch)
        else:
            if ch == "'":
                in_quote = True
            elif ch == ",":
                token = "".join(current).strip()
                result.append(None if token == "NULL" else token)
                current = []
                i += 1
                continue
            else:
                current.append(ch)
        i += 1

    # Append the last value
    token = "".join(current).strip()
    result.append(None if token == "NULL" else token)

    return result


def _split_row_tuples(values_block: str) -> list[str]:
    """
    Extract the inner content of each top-level ``(…)`` tuple in a VALUES block.

    Correctly handles SQL single-quoted strings (which may contain commas and
    parentheses) so that only structural parentheses are used as boundaries.

    Args:
        values_block: Everything after ``VALUES`` up to but not including the
                      trailing ``;``.

    Returns:
        List of strings, each being the raw content between the outer parens
        of one row, suitable for passing to :func:`_parse_sql_values`.
    """
    rows: list[str] = []
    depth = 0
    start = -1
    in_quote = False
    i = 0
    n = len(values_block)

    while i < n:
        ch = values_block[i]
        if in_quote:
            if ch == "'" and i + 1 < n and values_block[i + 1] == "'":
                # Escaped single-quote: skip both characters
                i += 2
                continue
            if ch == "'":
                in_quote = False
        else:
            if ch == "'":
                in_quote = True
            elif ch == "(" and depth == 0:
                depth = 1
                start = i + 1
            elif ch == "(":
                depth += 1
            elif ch == ")" and depth == 1:
                rows.append(values_block[start:i])
                depth = 0
                start = -1
            elif ch == ")":
                depth -= 1
        i += 1

    return rows


def _iter_statements_from_lines(lines: Iterator[str]) -> Iterator[str]:
    """
    Group an iterable of raw dump lines into logical INSERT statements.

    pg_dump may emit one statement across many physical lines (the ``VALUES``
    keyword and the row tuples land on separate lines, and a row containing a
    newline in a text column wraps). Those lines must be joined before the
    statement regex can match, so this buffers from an ``INSERT INTO`` up to
    the line that ends with ``;``.

    At most one statement is held at a time, which is what keeps the streaming
    path bounded regardless of total input size.

    Args:
        lines: Raw lines from the dump, with or without trailing newlines.

    Yields:
        Each complete logical ``INSERT`` statement, whitespace-normalised.
    """
    buffer: list[str] = []
    for raw_line in lines:
        # Bound the buffer so a malformed dump (an INSERT whose terminating
        # semicolon never arrives) cannot grow it without limit. Well-formed
        # input never reaches this: the statement is flushed at its semicolon.
        if len(buffer) > MAX_STATEMENT_LINES:
            yield " ".join(buffer)
            buffer = []

        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        if stripped.upper().startswith("INSERT INTO"):
            # A new INSERT supersedes anything buffered: the previous statement
            # never received its terminating semicolon (truncated dump).
            buffer = [stripped]
        elif buffer:
            buffer.append(stripped)

        if buffer and stripped.endswith(";"):
            yield " ".join(buffer)
            buffer = []

    # Trailing statement without a terminating semicolon.
    if buffer:
        yield " ".join(buffer)


def iter_sql_statements(sql_path: Path) -> Iterator[str]:
    """
    Stream logical INSERT statements out of a SQL dump file, one at a time.

    MOD-OPS-17: the previous implementation read the whole dump into a string
    and then accumulated *every* statement into a list, so peak memory was the
    input size plus a full second copy of it. A mature instance dump is
    routinely hundreds of MB, so conversion could OOM regardless of how small
    the resulting JSON was.

    This reads the file lazily and holds at most one statement. The file
    object's internal buffer is fixed-size and independent of file size.

    Args:
        sql_path: Path to the SQL dump.

    Yields:
        Each complete logical ``INSERT`` statement, whitespace-normalised.
    """
    # `errors="replace"` mirrors what a shell pipeline would do with a stray
    # invalid byte: step past it rather than abort a migration over one
    # non-UTF-8 byte in a text column.
    with open(sql_path, encoding="utf-8", errors="replace") as f:
        yield from _iter_statements_from_lines(f)


def iter_parsed_rows(statement: str) -> Iterator[tuple[str, list[str | None]]]:
    """
    Yield ``(table_name, values)`` for each row tuple in one INSERT statement.

    MOD-OPS-17: rows are yielded one at a time, so a caller never holds a whole
    table's worth of parsed rows.

    Args:
        statement: A single logical ``INSERT`` statement.

    Yields:
        ``(table_name, values)`` per row, where ``table_name`` is the bare
        table name and ``values`` holds the parsed column values (entries may
        be ``None`` for SQL NULL).
    """
    m = INSERT_RE.match(statement)
    if not m:
        return

    table_name = m.group(1)
    for row_content in _split_row_tuples(m.group(2)):
        yield table_name, _parse_sql_values(row_content)


def _row_to_record(table_name: str, values: list[str | None]) -> dict[str, Any] | None:
    """
    Convert one parsed row into the JSON record shape used by migrate_legacy.py.

    Args:
        table_name: Bare table name from the INSERT statement.
        values: Parsed column values.

    Returns:
        The record dict, or None when the table is unknown or the row has too
        few columns to be valid.
    """
    if table_name == "client" and len(values) >= 4:
        return {
            "id": values[0],
            "address": values[1],
            "user": values[2],
            "added": values[3],
        }

    if table_name == "manifestation" and len(values) >= 5:
        # Columns: id, isbn, title, authors, meta (JSON), added
        meta: dict[str, Any] = {}
        try:
            meta = json.loads(values[4]) if values[4] else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": values[0],
            "isbn": values[1],
            "title": values[2],
            "authors": values[3],
            "meta": meta,
            "added": values[5] if len(values) > 5 else None,
        }

    if table_name == "item" and len(values) >= 4:
        # Columns: id, manifestation_id, added_by, added_at, meta (JSON)
        item_meta: dict[str, Any] = {}
        try:
            item_meta = json.loads(values[4]) if len(values) > 4 and values[4] else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": values[0],
            "manifestation_id": values[1],
            "added_by": values[2],
            "added_at": values[3],
            "meta": item_meta,
        }

    return None


def convert_sql_dump(sql_path: Path, output_path: Path) -> dict[str, int]:
    """
    Convert a legacy SQL dump to the migrate_legacy.py JSON format, streaming.

    MOD-OPS-17: records are serialised to disk as they are parsed, so peak
    memory is bounded by one statement's worth of rows rather than by the size
    of the dump. The output remains a single valid JSON object with the same
    ``{"clients": [...], "manifestations": [...], "items": [...]}`` shape that
    ``migrate_legacy.py`` consumes, so downstream behaviour is unchanged.

    Implementation note: the output is grouped by collection, but a dump can
    interleave tables (pg_dump emits one statement block per table, yet a
    hand-edited or multi-schema dump need not). Buffering every record in RAM
    just to regroup it would reintroduce the very problem this function
    removes, so records are spooled one-per-line to a temporary JSONL file per
    collection and then streamed into the final document. Memory stays bounded
    by a single record and the assembly is a pure concatenation.

    Args:
        sql_path: Path to the input SQL dump.
        output_path: Path to the JSON file to write.

    Returns:
        Mapping of collection name to the number of records written.

    Raises:
        Exception: Any parsing or write error propagates after all partial
            artifacts are removed, so no half-written output can be mistaken
            for a complete conversion.
    """
    collections = ("clients", "manifestations", "items")
    counts = dict.fromkeys(collections, 0)

    spools: dict[str, Any] = {}
    spool_paths: list[Path] = []
    # Output goes to a sibling `.partial` file and is renamed only once
    # complete, so an interrupted run never leaves a truncated JSON file that a
    # later run would treat as a finished conversion.
    tmp_output = output_path.with_name(output_path.name + ".partial")

    try:
        for collection in collections:
            # `delete=False` is required, not an oversight: the three spools must
            # stay open simultaneously while every statement is parsed, and pass
            # 2 re-opens each one by path to stream it into the final document.
            # They are unlinked unconditionally in the `finally` block below, so
            # a crash cannot leave credential-bearing rows behind on disk.
            #
            # pylint: disable=consider-using-with  # see comment above
            handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode="w",
                encoding="utf-8",
                prefix=f"sql2json_{collection}_",
                suffix=".jsonl",
                delete=False,
            )
            spools[collection] = handle
            spool_paths.append(Path(handle.name))

        # ── Pass 1: parse and spool, one record at a time ──────────────────
        for statement in iter_sql_statements(sql_path):
            for table_name, values in iter_parsed_rows(statement):
                collection = COLLECTION_FOR_TABLE.get(table_name)
                if collection is None:
                    continue
                record = _row_to_record(table_name, values)
                if record is None:
                    continue
                # Newline-delimited: no separator state to carry between
                # records, so the spool stays line-parseable even if truncated.
                spools[collection].write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[collection] += 1

        for handle in spools.values():
            handle.close()

        # ── Pass 2: stream the spools into the final JSON document ───────
        with open(tmp_output, "w", encoding="utf-8") as out:
            out.write("{\n")
            for index, collection in enumerate(collections):
                if index:
                    out.write(",\n")
                out.write(f'  "{collection}": [')
                first = True
                with open(spool_paths[index], encoding="utf-8") as spool:
                    for line in spool:
                        line = line.strip()
                        if not line:
                            continue
                        if not first:
                            out.write(",")
                        out.write("\n    ")
                        out.write(line)
                        first = False
                out.write("\n  ]" if not first else "]")
            out.write("\n}\n")

        tmp_output.replace(output_path)
    finally:
        for handle in spools.values():
            if not handle.closed:
                handle.close()
        for path in spool_paths:
            path.unlink(missing_ok=True)
        tmp_output.unlink(missing_ok=True)

    return counts


def parse_sql_dump(sql_content: str) -> dict:
    """
    Parse a legacy SQL dump held in memory and extract data.

    Supports both quoted (``"iqoqo"."table"``) and unquoted (``iqoqo.table``)
    schema-qualified table names as produced by different pg_dump versions.

    Retained for callers and tests that already hold the dump as a string. New
    code should prefer :func:`convert_sql_dump`, which reads from a path and
    never materialises the whole dump in memory (MOD-OPS-17).

    Args:
        sql_content: Content of the SQL dump file.

    Returns:
        Dictionary containing clients, manifestations, and items.
    """
    data: dict[str, list] = {
        "clients": [],
        "manifestations": [],
        "items": [],
    }

    for statement in _iter_statements_from_lines(sql_content.splitlines()):
        for table_name, values in iter_parsed_rows(statement):
            record = _row_to_record(table_name, values)
            if record is None:
                continue
            data[COLLECTION_FOR_TABLE[table_name]].append(record)

    return data


def main():
    """Main entry point for SQL to JSON conversion."""
    parser = argparse.ArgumentParser(description="Convert legacy SQL dump to JSON format")
    parser.add_argument("input_file", help="Path to SQL dump file")
    parser.add_argument("output_file", help="Path to output JSON file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output_file)
    print(f"Converting SQL dump {input_path} -> {output_path} (streaming)...")
    counts = convert_sql_dump(input_path, output_path)

    print(f"Found {counts['clients']} clients")
    print(f"Found {counts['manifestations']} manifestations")
    print(f"Found {counts['items']} items")

    print("Conversion complete!")


if __name__ == "__main__":
    main()
