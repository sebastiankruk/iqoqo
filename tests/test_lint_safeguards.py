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
"""Tests to ensure no forbidden pylint suppressions exist in the codebase."""

import os
import re
import subprocess

import pytest

# A pylint disable directive, capturing the whole comma-separated code list.
#
# The list is captured rather than matched positionally because pylint accepts
# the codes in any order: `# pylint: disable=broad-exception-caught,
# too-many-return-statements` suppresses the second code just as effectively as
# listing it first. A regex that anchors the forbidden code to the start of the
# list therefore misses the common case of a developer appending it to an
# unrelated directive.
#
# `re.IGNORECASE` because pylint message names are case-insensitive, and `^\s*`
# so the directive is recognised when indented inside a function or class.
#
# The directive is NOT required to start the line. `re.search` rather than
# `re.match` is deliberate: the overwhelmingly common form in this codebase is
# a trailing comment on the `except` line --
# `except Exception:  # pylint: disable=broad-except` -- which an anchored
# pattern does not match at all. Anchoring is what made the original guard
# report zero findings against 23 real suppressions in `app/`: it was not a
# clean codebase, it was a blind regex.
_DIRECTIVE_RE = re.compile(r"#\s*pylint:\s*disable\s*=\s*(?P<codes>[^\n]*)", re.IGNORECASE)

# Every pylint message name that means "this handler catches Exception".
#
# `broad-except` (W0703) and `broad-exception-caught` (W0718) are two names for
# the same diagnostic, and pylint accepts either in a directive. Guarding only
# W0718 left the entire codebase free to suppress the check under its other
# name: 23 sites in app/ used `broad-except`, which is the *preferred* spelling
# a developer reaches for, and none of them were visible to the guard. A
# safeguard that can be evaded by using a synonym is not a safeguard, so both
# names are forbidden, as are the numeric codes for either.
#
# W0719 `broad-exception-raised` is not a suppression target -- it fires where
# code *raises* a bare Exception, which is a separate finding.
BROAD_EXCEPT_NAMES = frozenset(
    {
        "broad-except",
        "broad-exception-caught",
        "w0703",
        "w0718",
    }
)

#: Every deliberate broad-exception handler, as ``(file, enclosing function)``.
#: Read it as a review queue, not a permission slip: each entry is a place
#: where an unexpected exception type would otherwise escape, so each records a
#: decision about what the caller observes instead.
#:
#: The recurring shapes:
#:
#: * **Telemetry / audit bookkeeping** (`tasks.py`, `scanner.py`) — the catalog
#:   write already committed; failing to record a side-channel must not discard
#:   the work or fail the user's request.
#: * **Outbound third-party calls** (`lod_linking_service.py`, `admin.py`,
#:   `refetch_metadata.py`) — DBpedia, GeoNames, WordNet and the ISBN providers
#:   can raise anything from DNS to a 500. The result is an *enrichment*, so it
#:   degrades to "nothing found" and is recorded.
#: * **Auth and CSRF** (`decorators.py`) — deliberately fails closed.
#:   Enumerating driver and middleware exceptions would let a new one
#:   authenticate someone.
#: * **Best-effort ingest** (`manifestations.py`, `frbr_service.py`,
#:   `scanner.py`) — a failed auto-save falls back to locating the existing
#:   record rather than failing the request.
#: * **Cleanup in a `finally`** (`tasks.py`, `log_redaction.py`) — re-raising
#:   would mask the original failure.
#: * **Scripts and tests** — these report a failure and exit non-zero, or assert
#:   that nothing escaped. They are not request paths, so a broad catch that
#:   turns an unexpected error into a readable message is the intended shape.
#:
#: Adding a site here is deliberate: state in the commit message why the catch
#: is correct and what the caller observes. Removing a site whose handler has
#: been narrowed to specific exception types is the better move.
JUSTIFIED_BROAD_EXCEPT_SITES = frozenset(
    {
        # Telemetry bookkeeping after the catalog write has committed.
        ("app/api/scanner.py", "_record_scan_telemetry"),
        ("app/core/tasks.py", "batch_link_catalog_lod_task"),
        # Outbound authority / provider lookups: any failure means "no links".
        ("app/api/admin.py", "trigger_lod_reconciliation"),
        ("app/api/admin.py", "get_active_lod_task"),
        ("app/api/admin.py", "cancel_lod_reconciliation_task"),
        ("app/api/manifestations.py", "trigger_manifestation_semantic_relink"),
        ("app/core/lod_linking_service.py", "_query_lookup"),
        ("app/core/lod_linking_service.py", "_query_sparql"),
        ("app/core/lod_linking_service.py", "resolve_location"),
        ("scripts/refetch_metadata.py", "run_refetch"),
        # Auth and CSRF: must fail closed rather than raise past the decorator.
        ("app/api/decorators.py", "_account_is_usable"),
        ("app/api/decorators.py", "csrf_proof_from_request"),
        # Best-effort ingest / enrichment on an otherwise-successful write.
        ("app/api/manifestations.py", "persist_isbn_manifestation"),
        ("app/api/manifestations.py", "refetch_metadata"),
        ("app/core/frbr_service.py", "create_manifestation"),
        ("app/api/scanner.py", "lookup_barcode_preview"),
        # Log redaction must never be the reason a log call fails.
        ("app/core/log_redaction.py", "filter"),
        # Operational scripts: report and exit non-zero rather than traceback.
        ("scripts/sync_ontology.py", "_parse_turtle"),
        ("scripts/validate_yaml.py", "validate_yaml"),
        # Test asserting a malicious payload raises nothing unexpected.
        ("tests/test_core_fixes.py", "test_search_service_resists_sql_injection"),
    }
)


def suppressed_codes(line: str) -> set[str]:
    """Return the lowercase message names a `pylint: disable` on this line suppresses.

    @param line: One source line.
    @returns: The suppressed message names, lowercased. Empty when the line
        carries no disable directive.
    """
    match = _DIRECTIVE_RE.search(line)
    if not match:
        return set()
    return {code.strip().lower() for code in match.group("codes").split(",") if code.strip()}


#: Pre-existing `too-many-return-statements` suppressions, by
#: ``(file, function)``. The rule exists to push genuinely tangled functions
#: into a strategy object. These three are not that: each is a sequence of
#: *guard clauses* — authenticate, validate the payload, check the FRBR
#: hierarchy, detect the duplicate, then return the created resource — where
#: the early return is the correct expression of "this request is finished".
#: Collapsing them into a single exit would mean threading a result object
#: through seven branches, which is less readable rather than more.
#:
#: All three predate the anchored-regex fix that gave this guard the ability to
#: see a trailing `# pylint: disable=` comment at all, so it had never reviewed
#: them. Rewriting three HTTP handlers is not a same-commit change on a release
#: branch; recording them keeps the count honest and makes the next
#: simplification a decision rather than an oversight.
JUSTIFIED_TOO_MANY_RETURN_SITES = frozenset(
    {
        ("app/api/wishlist.py", "create_wishlist_item"),
        ("app/api/wishlist.py", "update_wishlist_item"),
        ("app/api/scanner.py", "scan_barcode"),
    }
)


def test_no_too_many_return_statements_disables():
    """
    Ensure no *unexplained* pylint directive suppresses 'too-many-return-statements'.

    See JUSTIFIED_TOO_MANY_RETURN_SITES for the three recorded exceptions and the
    reasoning behind them. A fourth requires an entry there.
    """
    import pytest

    forbidden = "too-many-return-statements"
    search_dir = "app"

    if not os.path.exists(search_dir):
        pytest.fail(f"Search directory '{search_dir}' does not exist.")

    violations = []

    for root, _, files in os.walk(search_dir):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, encoding="utf-8") as handle:
                    source = handle.readlines()
            except (OSError, UnicodeDecodeError) as e:
                violations.append(f"ERROR: Could not read {file_path}: {e}")
                continue

            for line_num, line in enumerate(source, 1):
                if forbidden not in suppressed_codes(line):
                    continue
                enclosing = "<module>"
                for prior in range(line_num - 1, -1, -1):
                    match = re.match(r"\s*(?:async )?def (\w+)", source[prior])
                    if match:
                        enclosing = match.group(1)
                        break
                key = (os.path.relpath(file_path, os.getcwd()), enclosing)
                if key not in JUSTIFIED_TOO_MANY_RETURN_SITES:
                    violations.append(f"{file_path}:{line_num}: {enclosing}() -- not in JUSTIFIED_TOO_MANY_RETURN_SITES")

    if violations:
        error_msg = (
            f"Forbidden pylint suppression of 'too-many-return-statements' in {len(violations)} location(s).\n"
            "Refactor the handler, or record it in JUSTIFIED_TOO_MANY_RETURN_SITES if the\n"
            "multiple returns are guard clauses rather than tangled control flow:\n"
        )
        error_msg += "\n".join(violations)
        pytest.fail(error_msg)


def test_no_broad_exception_caught_disables():
    """
    Ensure no pylint directive suppresses catching a bare Exception.

    Covers every name pylint accepts for the diagnostic -- see
    BROAD_EXCEPT_NAMES for why one name is not enough. The repository ships 23
    `broad-except` suppressions, all carrying a written justification of why
    the catch is deliberate, so they are not removed here; this test's job is to
    stop the count from growing and to make each one visible in one place.
    """
    import pytest

    search_dirs = ["app", "scripts", "tests"]
    violations = []

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue

        for root, _, files in os.walk(search_dir):
            for file in files:
                if not file.endswith(".py") or file == "test_lint_safeguards.py":
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, os.getcwd())
                try:
                    with open(file_path, encoding="utf-8") as f:
                        source = f.readlines()
                except (OSError, UnicodeDecodeError) as e:
                    violations.append(f"ERROR: Could not read {file_path}: {e}")
                    continue

                for line_num, line in enumerate(source, 1):
                    hit = suppressed_codes(line) & BROAD_EXCEPT_NAMES
                    if not hit:
                        continue
                    # Attribute the suppression to the function that encloses
                    # it, so the entry names a decision site rather than a
                    # line number that shifts on every unrelated edit.
                    enclosing = "<module>"
                    for prior in range(line_num - 1, -1, -1):
                        match = re.match(r"\s*(?:async )?def (\w+)", source[prior])
                        if match:
                            enclosing = match.group(1)
                            break
                    key = (rel_path, enclosing)
                    if key not in JUSTIFIED_BROAD_EXCEPT_SITES:
                        violations.append(
                            f"{rel_path}:{line_num}: {sorted(hit)} in {enclosing}() " "-- not in JUSTIFIED_BROAD_EXCEPT_SITES"
                        )

    if violations:
        header = (
            f"Unexplained broad-exception suppression in {len(violations)} location(s).\n\n"
            "If the handler genuinely must catch Exception, narrow it to the specific\n"
            "exceptions it expects where you can. If it truly cannot be narrowed, add\n"
            "(path, function) to JUSTIFIED_BROAD_EXCEPT_SITES and say in the commit\n"
            "message why the catch is correct and what the caller observes instead:\n"
        )
        pytest.fail(header + "\n".join(violations))


# ---------------------------------------------------------------------------
# The guards must not be bypassable (MOD-TEST-15)
# ---------------------------------------------------------------------------
#
# A safeguard whose own pattern can be evaded is worse than no safeguard: it is
# reported as working, and the code it is meant to keep out gets in anyway. The
# guards below use a real parser, so these tests pin that the parser covers the
# spellings pylint accepts.


@pytest.mark.parametrize(
    "line",
    [
        # The code on its own.
        "# pylint: disable=too-many-return-statements",
        # The realistic bypass: appended to an unrelated directive.
        "# pylint: disable=broad-exception-caught, too-many-return-statements",
        "# pylint: disable=broad-exception-caught,too-many-return-statements",
        # Spacing variants pylint accepts.
        "# pylint:disable=broad-exception-caught, too-many-return-statements",
        "# pylint: disable = broad-exception-caught, too-many-return-statements",
        "    # pylint: disable=broad-exception-caught, too-many-return-statements",
        "\t# pylint: disable=broad-exception-caught, too-many-return-statements",
        # Message names are case-insensitive.
        "# pylint: disable=TOO-MANY-RETURN-STATEMENTS",
        "# pylint: disable=too-Many-Return-Statements",
        # Trailing comma and whitespace.
        "# pylint: disable=too-many-return-statements, ",
    ],
)
def test_forbidden_codes_are_detected_in_any_position(line: str) -> None:
    """A forbidden code is found wherever it appears in the directive's list.

    The previous pattern anchored the code to the start of the list, so every one
    of the "appended to an unrelated directive" spellings above passed the guard
    while pylint still honoured the suppression.

    @param line: A source line carrying a pylint disable directive.
    @returns: Nothing; a missed suppression fails the test.
    """
    assert "too-many-return-statements" in suppressed_codes(line)


@pytest.mark.parametrize(
    "line",
    [
        "",
        # Quoted, so this is a string literal rather than a directive.
        "DOC = '# pylint: disable=too-many-return-statements'",
        "PROSE = 'use # pylint: disable=too-many-return-statements sparingly'",
        # `enable` re-enables rather than suppresses.
        "# pylint: enable=too-many-return-statements",
        # A longer name that merely starts with the forbidden one.
        "# pylint: disable=too-many-return-statements-but-not-really",
        # A different linter entirely.
        "# noqa: too-many-return-statements",
        "return 1  # type: ignore  # pylint: disable=invalid-name",
    ],
)
def test_non_directive_lines_are_not_flagged(line: str) -> None:
    """Only real directives are flagged, so the guard does not cry wolf.

    A rule that matches prose trains reviewers to ignore it and to suppress
    whatever it reports next -- including a genuine suppression.

    The two string-literal cases are the ones that matter most now that the
    pattern is unanchored: this file itself contains directive text as test data,
    and an unanchored `search` will match inside it. Each case is therefore
    closed-quoted, which is also how a real codebase quotes prose about lint.

    @param line: A source line that is not a pylint disable directive.
    @returns: Nothing; a false positive fails the test.
    """
    assert "too-many-return-statements" not in suppressed_codes(line)


def test_unrelated_directives_are_not_flagged() -> None:
    """A directive for other message names yields only those names.

    @returns: Nothing; an extra name fails the test.
    """
    codes = suppressed_codes("# pylint: disable=invalid-name, missing-module-docstring")

    assert codes == {"invalid-name", "missing-module-docstring"}


def test_the_real_repository_has_no_forbidden_suppressions() -> None:
    """The parser agrees with both guards on the current tree.

    A parser change that started matching nothing would silently disable both
    safeguards, so this asserts the tree is currently clean under it.

    @returns: Nothing; a forbidden suppression anywhere fails the test.
    """
    checked = 0
    broad_seen = 0
    for search_dir in ("app", "scripts", "tests"):
        for root, _, files in os.walk(search_dir):
            for file in files:
                if not file.endswith(".py") or file == os.path.basename(__file__):
                    continue
                path = os.path.join(root, file)
                with open(path, encoding="utf-8") as handle:
                    source = handle.readlines()
                for index, line in enumerate(source, 1):
                    codes = suppressed_codes(line)
                    checked += 1
                    if "too-many-return-statements" in codes:
                        enclosing = "<module>"
                        for prior in range(index - 1, -1, -1):
                            match = re.match(r"\s*(?:async )?def (\w+)", source[prior])
                            if match:
                                enclosing = match.group(1)
                                break
                        key = (os.path.relpath(path, os.getcwd()), enclosing)
                        assert key in JUSTIFIED_TOO_MANY_RETURN_SITES, (
                            f"{path}:{index}: {enclosing}() suppresses too-many-return-statements "
                            "without an entry in JUSTIFIED_TOO_MANY_RETURN_SITES"
                        )
                    if codes & BROAD_EXCEPT_NAMES:
                        broad_seen += 1
                        enclosing = "<module>"
                        for prior in range(index - 1, -1, -1):
                            match = re.match(r"\s*(?:async )?def (\w+)", source[prior])
                            if match:
                                enclosing = match.group(1)
                                break
                        key = (os.path.relpath(path, os.getcwd()), enclosing)
                        assert key in JUSTIFIED_BROAD_EXCEPT_SITES, (
                            f"{path}:{index}: {enclosing}() suppresses a broad exception "
                            "without an entry in JUSTIFIED_BROAD_EXCEPT_SITES"
                        )

    assert checked > 0, "no Python files were scanned, so the check proved nothing"
    # If this ever drops to zero the whitelist has gone stale and is no longer
    # being exercised; a whitelist nothing matches is indistinguishable from a
    # guard that does nothing.
    assert broad_seen > 0, (
        "no broad-exception suppressions found in the tree, so " "JUSTIFIED_BROAD_EXCEPT_SITES is untested -- remove the stale entries"
    )
