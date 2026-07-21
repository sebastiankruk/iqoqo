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
# tests/bash/refetch_metadata.bats
# Tests for scripts/refetch_metadata.py CLI behavior.

@test "refetch_metadata script exists" {
  [ -f "scripts/refetch_metadata.py" ]
}

@test "refetch_metadata syntax check" {
  run python3 -m py_compile scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}

@test "refetch_metadata functions importable" {
  run .venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from scripts.refetch_metadata import get_gap_query, determine_strategy, RATE_LIMITS
print('Functions importable')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Functions importable"* ]]
}

@test "refetch_metadata help shows --gap flag" {
  run .venv/bin/python scripts/refetch_metadata.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--gap"* ]]
}

@test "refetch_metadata help shows --dry-run flag" {
  run .venv/bin/python scripts/refetch_metadata.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
}

@test "refetch_metadata help shows --force flag" {
  run .venv/bin/python scripts/refetch_metadata.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--force"* ]]
}

@test "refetch_metadata help shows --limit flag" {
  run .venv/bin/python scripts/refetch_metadata.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--limit"* ]]
}

@test "refetch_metadata help shows --content-type flag" {
  run .venv/bin/python scripts/refetch_metadata.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--content-type"* ]]
}

@test "refetch_metadata help shows gap choices" {
  run .venv/bin/python scripts/refetch_metadata.py --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"format"* ]]
  [[ "$output" == *"publisher"* ]]
}
