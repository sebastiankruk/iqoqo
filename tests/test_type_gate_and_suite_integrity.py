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
    """A second definition of the same test name silently replaces the first across all tests/**/test_*.py."""
    paths = sorted(TESTS_DIR.rglob("test_*.py"))
    offenders: list[str] = []

    for path in paths:
        declared: dict[str, int] = {}
        for scope, methods in _declared_test_names(ast.parse(path.read_text(encoding="utf-8"))).items():
            for method_name in methods:
                full_name = f"{scope}.{method_name}" if scope != "<module>" else method_name
                declared[full_name] = declared.get(full_name, 0) + 1
        for name, count in sorted(declared.items()):
            if count > 1:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {name} defined {count} times")

    assert not offenders, (
        "these test names are defined more than once per module; the later "
        "definition wins and the earlier one never runs:\n  " + "\n  ".join(offenders)
    )


def test_no_orphaned_backend_script_or_e2e_test_files() -> None:
    """Every test file must be discovered by its canonical runner without silent orphans."""
    from scripts import run_tests_parallel

    # 1. Parallel runner must include every non-PG-gated tests/**/test_*.py file
    expected_backend = {
        p.relative_to(REPO_ROOT).as_posix()
        for p in sorted(TESTS_DIR.rglob("test_*.py"))
        if not p.relative_to(REPO_ROOT).as_posix().startswith("tests/integration/db/")
    }
    parallel_discovered = set(run_tests_parallel.get_all_test_files())
    missing_parallel = sorted(expected_backend - parallel_discovered)
    assert not missing_parallel, f"Orphaned test files missed by scripts/run_tests_parallel.py: {missing_parallel}"

    # 2. Makefile test-scripts-python must include tests/scripts/
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    scripts_target = makefile_text.split("test-scripts-python:", 1)[1].split("\n\n", 1)[0]
    assert "tests/scripts/" in scripts_target, "test-scripts-python must include tests/scripts/"

    # 3. No orphaned frontend/tests/e2e directory outside Playwright's __tests__/e2e testDir
    orphaned_e2e_dir = REPO_ROOT / "frontend" / "tests" / "e2e"
    assert (
        not orphaned_e2e_dir.exists()
    ), f"Orphaned E2E directory {orphaned_e2e_dir} exists outside Playwright testDir frontend/__tests__/e2e"


def test_module_coverage_across_app_scripts_and_frontend() -> None:
    """Verify every app module, operational script, and frontend module has test coverage or explicit exemption."""
    backend_test_corpus = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in sorted(TESTS_DIR.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
    )

    # 1. Every non-__init__.py module in app/ must be referenced in tests/
    uncovered_app = []
    for py_file in sorted((REPO_ROOT / "app").rglob("*.py")):
        if py_file.name == "__init__.py" or "__pycache__" in py_file.parts:
            continue
        mod = py_file.with_suffix("").relative_to(REPO_ROOT).as_posix().replace("/", ".")
        if mod not in backend_test_corpus and py_file.stem not in backend_test_corpus:
            uncovered_app.append(py_file.relative_to(REPO_ROOT).as_posix())
    assert not uncovered_app, f"Backend app modules with no test reference: {uncovered_app}"

    # 2. Operational scripts in scripts/ must be referenced in tests/ (excluding bounded standalone dev utilities)
    script_exemptions = {
        "scripts/allegro_auth.py",
        "scripts/benchmark_graph_backends.py",
        "scripts/maintain_deploy_dir.py",
        "scripts/phash_cover.py",
        "scripts/run_secret_scan.py",
        "scripts/setup-ios-tools.sh",
        "scripts/update_bgg_mechanics.py",
    }
    uncovered_scripts = []
    for script_file in sorted((REPO_ROOT / "scripts").rglob("*")):
        if not script_file.is_file() or "__pycache__" in script_file.parts or script_file.suffix not in {".py", ".sh"}:
            continue
        rel = script_file.relative_to(REPO_ROOT).as_posix()
        if rel in script_exemptions:
            continue
        if script_file.name not in backend_test_corpus and script_file.stem not in backend_test_corpus:
            uncovered_scripts.append(rel)
    assert not uncovered_scripts, f"Operational scripts with no test reference: {uncovered_scripts}"

    # 3. Frontend modules under app/, components/, lib/, hooks/ must be referenced in __tests__/ or allowlisted
    fe_root = REPO_ROOT / "frontend"
    fe_test_corpus = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in list((fe_root / "__tests__").rglob("*")) + list((fe_root / "tests").rglob("*"))
        if p.is_file()
    )
    fe_exemptions = {
        "app/account/delete/page.tsx",
        "app/account/verify/page.tsx",
        "app/admin/federation/page.tsx",
        "app/admin/groups/page.tsx",
        "app/admin/sparql/page.tsx",
        "app/apple-icon.tsx",
        "app/help/[slug]/page.tsx",
        "app/legal/privacy/page.tsx",
        "app/legal/terms/page.tsx",
        "components/admin/cover-editor/editor-toolbar.tsx",
        "components/admin/frbr/manifestation-editor.tsx",
        "components/help/help-article-detail-client.tsx",
        "components/item/discovery-pivot.tsx",
        "components/item/extended-metadata-puzzle.tsx",
        "components/item/sidebar/constants.ts",
        "components/item/sidebar/use-item-sidebar-actions.ts",
        "components/social/frbr-notes.tsx",
        "components/ui/bgg-attribution.tsx",
        "components/ui/bibliographic-attribution.tsx",
        "components/ui/discogs-attribution.tsx",
        "components/ui/igdb-attribution.tsx",
        "components/ui/tmdb-attribution.tsx",
        "lib/api/server-client.ts",
    }
    uncovered_fe = []
    for folder in ("app", "components", "lib", "hooks"):
        for fe_file in sorted((fe_root / folder).rglob("*")):
            if fe_file.suffix not in {".ts", ".tsx"} or fe_file.name.endswith(".d.ts"):
                continue
            rel = fe_file.relative_to(fe_root).as_posix()
            if rel in fe_exemptions:
                continue
            key = fe_file.parent.relative_to(fe_root).as_posix() if fe_file.stem in {"page", "layout", "route"} else fe_file.stem
            rel_no_ext = rel.removesuffix(".tsx").removesuffix(".ts")
            if key not in fe_test_corpus and rel_no_ext not in fe_test_corpus:
                uncovered_fe.append(rel)
    assert not uncovered_fe, f"Frontend modules with no test reference: {uncovered_fe}"


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
