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
# tests/bash/format_mappings_validation.bats
# Validates shared/format_mappings.yaml.

@test "format_mappings.yaml exists" {
  [ -f "shared/format_mappings.yaml" ]
}

@test "format_mappings.yaml is valid YAML" {
  run .venv/bin/python -c "
import yaml
with open('shared/format_mappings.yaml', 'r') as f:
    data = yaml.safe_load(f)
print('YAML parsed successfully')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"YAML parsed successfully"* ]]
}

@test "format_mappings.yaml contains format_normalizations key" {
  run .venv/bin/python -c "
import yaml
with open('shared/format_mappings.yaml', 'r') as f:
    data = yaml.safe_load(f)
assert 'format_normalizations' in data, 'Missing key'
print('format_normalizations key found')
"
  [ "$status" -eq 0 ]
}

@test "format_mappings.yaml is not empty" {
  run .venv/bin/python -c "
import yaml
with open('shared/format_mappings.yaml', 'r') as f:
    data = yaml.safe_load(f)
norms = data.get('format_normalizations', {})
assert norms, 'Empty'
print('format_normalizations entries:', len(norms))
"
  [ "$status" -eq 0 ]
}

@test "format_mappings.yaml has valid source/target structure" {
  run .venv/bin/python -c "
import yaml
with open('shared/format_mappings.yaml', 'r') as f:
    data = yaml.safe_load(f)
norms = data.get('format_normalizations', {})
for key, value in norms.items():
    if key == 'null':
        assert isinstance(value, dict), f'null value should be dict'
        for ct, target in value.items():
            assert isinstance(target, str), f'null/{ct} should be str'
    else:
        assert isinstance(value, str), f'{key} should be str'
print('Structure validation passed')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Structure validation passed"* ]]
}
