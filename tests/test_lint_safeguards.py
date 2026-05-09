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
import subprocess

def test_no_too_many_return_statements_disables():
    """
    Ensure that 'too-many-return-statements' is not disabled in the app/ directory.
    This enforces clean refactoring into Strategy patterns.
    """
    search_pattern = "pylint: disable=too-many-return-statements"
    search_dir = "app/"
    
    # Use grep to find the pattern
    try:
        result = subprocess.run(
            ["grep", "-r", search_pattern, search_dir],
            capture_output=True,
            text=True,
            check=False
        )
        
        # If grep finds something, it returns 0
        if result.returncode == 0:
            found_lines = result.stdout.strip().split("\n")
            error_msg = f"Forbidden pylint suppression found in {len(found_lines)} locations:\n"
            error_msg += "\n".join(found_lines)
            pytest_fail(error_msg)
        
    except FileNotFoundError:
        # Fallback if grep is not available (unlikely on Mac/Linux)
        pass

def pytest_fail(message):
    """Helper to fail the test with a message."""
    import pytest
    pytest.fail(message)
