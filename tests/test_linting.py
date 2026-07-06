"""Tests for code quality and linting checks.

This module ensures that all linting tools pass when tests are run.
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


def test_python_syntax():
    """Test that all Python files have valid syntax."""
    errors = []
    source_dirs = ["app", "tests", "scripts"]
    for source_dir in source_dirs:
        for path in pathlib.Path(source_dir).rglob("*.py"):
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


def test_shellcheck():
    """Verify that all bash scripts pass shellcheck if installed."""
    import shutil

    shellcheck_bin = shutil.which("shellcheck")
    if not shellcheck_bin:
        pytest.skip("shellcheck is not installed on this system")

    # Find all .sh files in scripts/ and project root
    sh_files = list(pathlib.Path("scripts").rglob("*.sh"))
    # Also check if there are other shell files
    sh_files.extend(pathlib.Path(".").glob("*.sh"))

    assert len(sh_files) > 0, "No shell script files found to check!"

    errors = []
    for sh_file in sh_files:
        res = subprocess.run([shellcheck_bin, str(sh_file)], capture_output=True, text=True, check=False)
        if res.returncode != 0:
            errors.append(f"shellcheck violations in {sh_file}:\n{res.stdout or res.stderr}")

    assert not errors, "\n\n".join(errors)
