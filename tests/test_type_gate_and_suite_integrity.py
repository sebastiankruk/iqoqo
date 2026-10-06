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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Guards that keep the type gate and the test suite structurally honest.

Both checks here exist because a gate that reports success while checking
nothing is worse than no gate at all: it is reported as working while the code
it excludes gets in. The release that added these had exactly that shape, in
two independent places, and nothing in the suite could see either one.
"""

from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"


# ---------------------------------------------------------------------------
# The type gate must actually run
# ---------------------------------------------------------------------------


def _mypy_configured_paths() -> list[str]:
    """The paths the canonical mypy invocation is meant to check."""
    runner = (REPO_ROOT / "scripts" / "run_lint.py").read_text(encoding="utf-8")
    tree = ast.parse(runner)
    for node in ast.walk(tree):
        # Each canonical check is a 4-tuple: (label, argv, cwd, blocking).
        if not isinstance(node, ast.Tuple) or len(node.elts) != 4:
            continue
        label, command = node.elts[0], node.elts[1]
        if isinstance(label, ast.Constant) and str(label.value).startswith("Mypy"):
            assert isinstance(command, ast.List), "mypy command should be a literal list"
            return [ast.literal_eval(element) for element in command.elts if isinstance(element, ast.Constant)]
    pytest.fail("no Mypy entry found in scripts/run_lint.py CANONICAL_JOBS")


def test_the_canonical_mypy_invocation_checks_the_test_suite() -> None:
    """`tests/` must be in the mypy argument list.

    `tests/` was present, so this passes for the wrong reason if the check ever
    moves. What actually broke the gate was not the path list but `tests/`
    having no `__init__.py` while a test imported a sibling helper as
    `tests.<module>` -- see the next test, which is the one that bites.
    """
    paths = _mypy_configured_paths()

    assert "app/" in paths, f"mypy must check the application, got {paths}"
    assert "tests/" in paths, f"mypy must check the test suite, got {paths}"


def test_mypy_does_not_resolve_any_test_file_under_two_module_names() -> None:
    """No test may import a sibling helper via a `tests.`-prefixed module name.

    `tests/` deliberately has no `__init__.py`. That is a valid pytest layout --
    pytest's rootdir insertion puts the test directory on `sys.path` -- but it
    means a file under `tests/` is simultaneously reachable as two modules:
    the top-level `phash_corpus` and the package-style `tests.phash_corpus`.

    mypy refuses that ambiguity and aborts with::

        error: Source file found twice under different module names:
            "phash_corpus" and "tests.phash_corpus"
        Found 1 error in 1 file (errors prevented further checking)

    That is fatal rather than per-file: **no** file gets checked. The gate then
    reports a type error, is marked non-blocking in CI, and goes on checking
    nothing for the rest of the branch's life -- while a reader reasonably
    concludes the codebase is type-clean.
    """
    offenders: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("tests."):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: from {node.module} import ...")

    assert not offenders, (
        "these imports resolve a sibling test helper under two module names, which "
        "aborts mypy before it checks anything:\n  " + "\n  ".join(offenders)
    )


def test_mypy_actually_reports_its_checked_file_count() -> None:
    """mypy must get past module resolution and report a file count.

    The two tests above constrain *how* mypy is invoked; this one observes the
    result. It tolerates type *errors* -- the backlog is real and is tracked in
    the changelog -- but not the failure mode where mypy checks zero files. The
    distinguishing signals are ``errors prevented further checking`` and an
    absent ``(checked N source files)`` suffix, both of which are what a
    resolution abort looks like from the outside.
    """
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "app/", "tests/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr

    assert "errors prevented further checking" not in output, (
        "mypy aborted during module resolution, so it type-checked nothing:\n" + output[-2000:]
    )
    assert "Found 1 error in 1 file (errors prevented" not in output, "mypy aborted during module resolution:\n" + output[-2000:]
    assert "source file" in output, f"mypy reported no checked-file count:\n{output[-2000:]}"


# ---------------------------------------------------------------------------
# The test suite must not shadow itself
# ---------------------------------------------------------------------------


def _declared_test_names(tree: ast.Module) -> dict[str, list[str]]:
    """Map a fully-qualified definition name to the test methods declared on it."""
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            found[node.name] = [
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_")
            ]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            found.setdefault("<module>", []).append(node.name)
    return found


def test_no_test_class_or_function_is_defined_twice_in_one_file() -> None:
    """A second definition of the same test name silently replaces the first.

    The account-deletion suite defined three of its classes twice -- once in a
    block that had been superseded and again, byte-identical, at the bottom of
    the file. Python binds the later one, so the earlier copy never ran and
    nothing reported it: ``pytest`` collected 56 tests while the file declared
    66, and the ten unreachable tests sat in the highest-risk security suite in
    the repository.

    A maintainer editing the dead copy gets green tests as feedback, because
    the live copy still passes. This check is deliberately a plain AST scan
    rather than a diff against ``main``: the defect is not that a copy is old,
    it is that a name is bound twice in one module.

    Bounded to the account-deletion suite today, but the check is generic and
    the scan is cheap -- widen ``paths`` rather than adding a second copy of
    this test.
    """
    paths = [TESTS_DIR / "test_account_deletion.py"]
    offenders: list[str] = []

    for path in paths:
        declared: dict[str, int] = {}
        for name in _declared_test_names(ast.parse(path.read_text(encoding="utf-8"))):
            declared[name] = declared.get(name, 0) + 1
        for name, count in sorted(declared.items()):
            if count > 1:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {name} defined {count} times")

    assert not offenders, (
        "these test names are defined more than once per module; the later "
        "definition wins and the earlier one never runs:\n  " + "\n  ".join(offenders)
    )


def test_the_account_deletion_suite_declares_exactly_what_pytest_collects() -> None:
    """Declared test count must equal collected test count.

    A module that loses tests between the AST and the collector has a shadowing
    problem, which is the defect this file exists to catch. This is the
    observable consequence of the check above, asserted directly so that a
    *future* instance is caught even if it appears in a file the `paths` list
    above has not been widened to include.
    """
    path = TESTS_DIR / "test_account_deletion.py"
    declared = sum(len(methods) for methods in _declared_test_names(ast.parse(path.read_text(encoding="utf-8"))).values())

    result = subprocess.run(
        [sys.executable, "-m", "pytest", f"{path.relative_to(REPO_ROOT)}", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    collected = 0
    for line in result.stdout.splitlines():
        # e.g. "56 tests collected in 0.09s" or "...\n1 test collected".
        match = re.search(r"(\d+)\s+tests?\s+collected", line)
        if match:
            collected = int(match.group(1))

    assert collected, f"pytest collected nothing from {path}:\n{result.stdout[-2000:]}"
    assert declared == collected, (
        f"{path.relative_to(REPO_ROOT)} declares {declared} test functions but pytest "
        f"collects {collected}. The {declared - collected} difference is shadowed "
        "definitions: defined but never run."
    )
