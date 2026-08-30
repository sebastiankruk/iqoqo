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
# tests/bash/makefile_tooling.bats
# Tests for Makefile targets related to tooling scripts.

@test "Makefile has fix-physical-kinds target" {
  run grep -E '^fix-physical-kinds:' Makefile
  [ "$status" -eq 0 ]
}

@test "Makefile fix-physical-kinds target invokes fix_physical_kinds.py" {
  run make -n fix-physical-kinds
  [ "$status" -eq 0 ]
  [[ "$output" == *"fix_physical_kinds.py"* ]]
}

@test "Makefile has refetch-metadata target" {
  run grep -E '^refetch-metadata:' Makefile
  [ "$status" -eq 0 ]
}

@test "Makefile refetch-metadata target invokes refetch_metadata.py" {
  run make -n refetch-metadata
  [ "$status" -eq 0 ]
  [[ "$output" == *"refetch_metadata.py"* ]]
}

@test "Makefile fix-physical-kinds target passes ARGS" {
  run make -n fix-physical-kinds ARGS="--audit"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--audit"* ]]
}

@test "Makefile refetch-metadata dry-run flag passed" {
  run make -n refetch-metadata dry-run=true
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
}

@test "Makefile refetch-metadata force flag passed" {
  run make -n refetch-metadata force=true
  [ "$status" -eq 0 ]
  [[ "$output" == *"--force"* ]]
}

@test "Makefile refetch-metadata limit flag passed" {
  run make -n refetch-metadata limit=10
  [ "$status" -eq 0 ]
  [[ "$output" == *"--limit"* ]]
  [[ "$output" == *"10"* ]]
}

@test "Makefile fix-physical-kinds apply and dry-run flags passed" {
  run make -n fix-physical-kinds ARGS="--apply --dry-run"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--apply"* ]]
  [[ "$output" == *"--dry-run"* ]]
}

@test "Makefile fix-physical-kinds interactive flag passed" {
  run make -n fix-physical-kinds ARGS="--interactive"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--interactive"* ]]
}

@test "Makefile lint-python in standard mode outputs echo commands" {
  run make -n lint-python
  [ "$status" -eq 0 ]
  [[ "$output" == *"echo \"Running ruff...\""* ]]
  [[ "$output" == *"echo \"Running mypy...\""* ]]
  [[ "$output" == *"echo \"Running pylint...\""* ]]
}

@test "Makefile lint-python in AI mode suppresses echo commands and adds terse flags" {
  run make -n lint-python IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" != *"echo \"Running ruff...\""* ]]
  [[ "$output" == *"--output-format=concise"* ]]
  [[ "$output" == *"--no-error-summary"* ]]
  [[ "$output" == *"--msg-template="* ]]
}

@test "Makefile test-backend in AI mode suppresses echo commands" {
  run make -n test-backend IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" != *"echo \"Running backend tests...\""* ]]
}
