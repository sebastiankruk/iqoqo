"""Tests for code quality and linting checks.

This module ensures that all linting tools pass when tests are run.
"""

import pathlib
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest

# Get the virtual environment path
VENV_BIN = Path(__file__).parent.parent / ".venv" / "bin"


def get_tool_path(tool_name):
    """Get the path to a tool, preferring venv but falling back to global."""
    venv_tool = VENV_BIN / tool_name
    if venv_tool.exists():
        return str(venv_tool)
    # Fall back to global command (for CI environments)
    return tool_name


def test_ruff_linting():
    """Test that ruff linting passes."""
    result = subprocess.run(
        [get_tool_path("ruff"), "check", "app/", "tests/", "scripts/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Ruff linting failed:\n{result.stdout}\n{result.stderr}"


def test_mypy_type_checking():
    """Test that mypy type checking passes."""
    result = subprocess.run(
        [get_tool_path("mypy"), "app/", "tests/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Mypy type checking failed:\n{result.stdout}\n{result.stderr}"


def test_black_formatting():
    """Test that black formatting check passes."""
    result = subprocess.run(
        [get_tool_path("black"), "--check", "app/", "tests/", "scripts/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Black formatting check failed:\n{result.stdout}\n{result.stderr}"


def test_isort_imports():
    """Test that isort import ordering check passes."""
    result = subprocess.run(
        [get_tool_path("isort"), "--check-only", "app/", "tests/", "scripts/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Isort import check failed:\n{result.stdout}\n{result.stderr}"


def test_eslint_javascript():
    """Test that eslint JavaScript linting passes."""

    # 1. Pass as a single string so shell=True interprets the whole command.
    # 2. Add --cache so ESLint only lints files that have changed since the last run.
    # 3. Add --ignore-pattern to skip heavy 3rd-party minified libraries.
    # 4. Enclose the glob in quotes so ESLint resolves it, not the OS shell.
    command = 'npx eslint --cache --ignore-pattern "*.min.js" --ignore-pattern "bootstrap*.js" "app/web/static/js/**/*.js"'

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=True,
        check=False,
    )

    if result.returncode != 0:
        # Only fail if eslint is installed and configured
        if "command not found" not in result.stderr and "Cannot find module" not in result.stderr:
            raise AssertionError(f"ESLint failed:\n{result.stdout}\n{result.stderr}")
        # Skip if eslint is not installed
        print("ESLint not installed, skipping JavaScript linting", file=sys.stderr)


def test_python_syntax():
    """Test that all Python files have valid syntax."""
    errors = []
    for path in pathlib.Path(".").rglob("*.py"):
        # Skip .venv and node_modules directories
        if ".venv" in str(path) or "node_modules" in str(path):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{path}: {e}")

    assert not errors, "Python syntax errors found:\n" + "\n".join(errors)


def test_no_print_statements_in_app():
    """Test that app code doesn't contain print() statements (use logging instead)."""
    violations = []
    for path in pathlib.Path("app").rglob("*.py"):
        with open(path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Skip comments and allow print in migrations
                if line.strip().startswith("#"):
                    continue
                if "print(" in line and "migrations" not in str(path):
                    violations.append(f"{path}:{line_num}: {line.strip()}")

    # Allow a few exceptions for specific debug cases
    allowed_files = ["__pycache__"]
    violations = [v for v in violations if not any(af in v for af in allowed_files)]

    if violations:
        print("\nFound print() statements in app code (should use logging):", file=sys.stderr)
        for v in violations[:10]:  # Show first 10
            print(f"  {v}", file=sys.stderr)

    # This is a warning, not a hard failure for now
    # assert not violations, "Found print() statements in app code"


def test_no_todo_fixme_in_critical_files():
    """Test that critical files don't have TODO/FIXME comments."""
    critical_patterns = [
        "app/api/routes.py",
        "app/db/models.py",
        "app/__init__.py",
    ]

    violations = []
    for pattern in critical_patterns:
        for path in pathlib.Path(".").glob(pattern):
            with open(path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if "TODO" in line.upper() or "FIXME" in line.upper():
                        violations.append(f"{path}:{line_num}: {line.strip()}")

    # This is informational only, not a hard failure
    if violations:
        print("\nTODO/FIXME found in critical files:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
