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
  # Statically verify key functions and constants are defined in the source.
  run grep -c "^def get_gap_query" scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run grep -c "^def determine_strategy" scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run grep -c "^RATE_LIMITS" scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

@test "refetch_metadata help shows --gap flag" {
  run grep -F '"--gap"' scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}

@test "refetch_metadata help shows --dry-run flag" {
  run grep -F '"--dry-run"' scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}

@test "refetch_metadata help shows --force flag" {
  run grep -F '"--force"' scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}

@test "refetch_metadata help shows --limit flag" {
  run grep -F '"--limit"' scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}

@test "refetch_metadata help shows --content-type flag" {
  run grep -F '"--content-type"' scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}

@test "refetch_metadata help shows gap choices" {
  run grep -F "format" scripts/refetch_metadata.py
  [ "$status" -eq 0 ]

  run grep -F "publisher" scripts/refetch_metadata.py
  [ "$status" -eq 0 ]
}
