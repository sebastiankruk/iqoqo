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
  run .venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from scripts.fix_physical_kinds import audit_mode, apply_mode, MAPPINGS_FILE
print('Functions importable')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Functions importable"* ]]
}

@test "fix_physical_kinds cannot combine --apply and --interactive" {
  run .venv/bin/python scripts/fix_physical_kinds.py --apply --interactive
  [ "$status" -ne 0 ]
}

@test "fix_physical_kinds dry-run requires apply" {
  run .venv/bin/python scripts/fix_physical_kinds.py --dry-run
  [ "$status" -ne 0 ]
}

@test "fix_physical_kinds help shows --apply flag" {
  run .venv/bin/python scripts/fix_physical_kinds.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--apply"* ]]
}

@test "fix_physical_kinds help shows --interactive flag" {
  run .venv/bin/python scripts/fix_physical_kinds.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--interactive"* ]]
}

@test "fix_physical_kinds help shows --dry-run flag" {
  run .venv/bin/python scripts/fix_physical_kinds.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
}
