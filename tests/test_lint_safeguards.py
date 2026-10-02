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
_DIRECTIVE_RE = re.compile(r"^\s*#\s*pylint:\s*disable\s*=\s*(?P<codes>[^\n]*)", re.IGNORECASE)


def suppressed_codes(line: str) -> set[str]:
    """Return the lowercase message names a `pylint: disable` on this line suppresses.

    @param line: One source line.
    @returns: The suppressed message names, lowercased. Empty when the line
        carries no disable directive.
    """
    match = _DIRECTIVE_RE.match(line)
    if not match:
        return set()
    return {code.strip().lower() for code in match.group("codes").split(",") if code.strip()}


def test_no_too_many_return_statements_disables():
    """
    Ensure that 'too-many-return-statements' is not disabled in the app/ directory.
    This enforces clean refactoring into Strategy patterns.

    Uses anchored regex so the check only triggers on actual pylint directive comments
    (optionally preceded by code), not on occurrences inside docstrings or string literals.
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
                with open(file_path, encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if forbidden in suppressed_codes(line):
                            violations.append(f"{file_path}:{line_num}: {line.strip()}")
            except (OSError, UnicodeDecodeError) as e:
                # Optionally handle or fail on unreadable files
                violations.append(f"ERROR: Could not read {file_path}: {e}")

    if violations:
        error_msg = f"Forbidden pylint suppression found in {len(violations)} locations:\n"
        error_msg += "\n".join(violations)
        pytest.fail(error_msg)


def test_no_broad_exception_caught_disables():
    """
    Ensure that 'broad-exception-caught' is not disabled in the app/, scripts/, and tests/ directories.

    Uses anchored regex so the check only triggers on actual pylint directive comments
    (optionally preceded by code), not on occurrences inside docstrings or string literals.
    """
    import pytest

    forbidden = "broad-exception-caught"
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
                try:
                    with open(file_path, encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            if forbidden in suppressed_codes(line):
                                violations.append(f"{file_path}:{line_num}: {line.strip()}")
                except (OSError, UnicodeDecodeError) as e:
                    violations.append(f"ERROR: Could not read {file_path}: {e}")

    if violations:
        error_msg = f"Forbidden pylint suppression of 'broad-exception-caught' found in {len(violations)} locations:\n"
        error_msg += "\n".join(violations)
        pytest.fail(error_msg)


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
        "return 1  # pylint: disable=too-many-return-statements",
        '# pylint: disable="too-many-return-statements"',
        "DOC = '# pylint: disable=too-many-return-statements'",
        "# pylint: enable=too-many-return-statements",
        "# pylint: disable=too-many-return-statements-but-not-really",
        "# noqa: too-many-return-statements",
    ],
)
def test_non_directive_lines_are_not_flagged(line: str) -> None:
    """Only real directives are flagged, so the guard does not cry wolf.

    A rule that matches prose trains reviewers to ignore it and to suppress
    whatever it reports next -- including a genuine suppression.

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
    for search_dir in ("app", "scripts", "tests"):
        for root, _, files in os.walk(search_dir):
            for file in files:
                if not file.endswith(".py") or file == os.path.basename(__file__):
                    continue
                path = os.path.join(root, file)
                with open(path, encoding="utf-8") as handle:
                    for line in handle:
                        codes = suppressed_codes(line)
                        checked += 1
                        assert "too-many-return-statements" not in codes, f"{path}: {line.strip()}"
                        assert "broad-exception-caught" not in codes, f"{path}: {line.strip()}"

    assert checked > 0, "no Python files were scanned, so the check proved nothing"
