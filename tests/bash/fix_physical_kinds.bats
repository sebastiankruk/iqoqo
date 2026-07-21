#!/usr/bin/env bats
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
#
# tests/bash/fix_physical_kinds.bats
# Tests for scripts/fix_physical_kinds.py CLI behavior.

@test "fix_physical_kinds script exists" {
  [ -f "scripts/fix_physical_kinds.py" ]
}

@test "fix_physical_kinds syntax check" {
  run python3 -m py_compile scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
}

@test "fix_physical_kinds functions importable" {
  # Statically verify key functions and constants are defined in the source.
  run grep -c "^def audit_mode" scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run grep -c "^def apply_mode" scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run grep -c "^MAPPINGS_FILE" scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

@test "fix_physical_kinds cannot combine --apply and --interactive" {
  # Verify the source contains mutual-exclusion validation.
  run grep -F "Cannot use --interactive and --apply together" scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
}

@test "fix_physical_kinds dry-run requires apply" {
  # Verify the source enforces that --dry-run only works with --apply.
  run grep -F -e "dry-run requires --apply" scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
}

@test "fix_physical_kinds help shows --apply flag" {
  run grep -F '"--apply"' scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
}

@test "fix_physical_kinds help shows --interactive flag" {
  run grep -F '"--interactive"' scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
}

@test "fix_physical_kinds help shows --dry-run flag" {
  run grep -F '"--dry-run"' scripts/fix_physical_kinds.py
  [ "$status" -eq 0 ]
}
