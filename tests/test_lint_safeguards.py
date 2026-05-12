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
    import pytest

    forbidden_pattern = "pylint: disable=too-many-return-statements"
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
                        if forbidden_pattern in line:
                            violations.append(f"{file_path}:{line_num}: {line.strip()}")
            except (OSError, UnicodeDecodeError) as e:
                # Optionally handle or fail on unreadable files
                violations.append(f"ERROR: Could not read {file_path}: {e}")

    if violations:
        error_msg = f"Forbidden pylint suppression found in {len(violations)} locations:\n"
        error_msg += "\n".join(violations)
        pytest.fail(error_msg)
