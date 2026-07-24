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
# tests/bash/validate_yaml.bats
# Tests for the Makefile validate-yaml target and validate_yaml.py script.

setup() {
  # Create a temporary directory for test YAML files
  TEST_DIR="$(mktemp -d)"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

@test "validate_yaml.py exits 0 for valid YAML" {
  echo "key: value" > "${TEST_DIR}/valid.yaml"
  run python scripts/validate_yaml.py
  # The default validates shared/format_mappings.yaml which should be valid
  [ "$status" -eq 0 ]
}

@test "validate_yaml.py exits 1 for malformed YAML file" {
  echo "key: value\n  bad indent" > "${TEST_DIR}/bad.yaml"
  run python -c "
import sys
sys.path.insert(0, 'scripts')
from validate_yaml import validate_yaml
try:
    validate_yaml('${TEST_DIR}/bad.yaml')
except SystemExit as e:
    sys.exit(e.code)
"
  [ "$status" -eq 1 ]
}

@test "validate_yaml.py exits 1 for missing file" {
  run python -c "
import sys
sys.path.insert(0, 'scripts')
from validate_yaml import validate_yaml
try:
    validate_yaml('${TEST_DIR}/nonexistent.yaml')
except SystemExit as e:
    sys.exit(e.code)
"
  [ "$status" -eq 1 ]
}

@test "Makefile validate-yaml target exists" {
  run grep -E '^validate-yaml:' Makefile
  [ "$status" -eq 0 ]
}

@test "Makefile validate-yaml --dry-run invokes the script" {
  run make -n validate-yaml
  [ "$status" -eq 0 ]
  [[ "$output" == *"validate_yaml.py"* ]]
}
