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
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "init_db.py --reset blocks in production environment without ALLOW_PROD_RESET" {
  FLASK_ENV=production run .venv/bin/python scripts/init_db.py --reset
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Refusing to reset database in production environment" ]]
}

@test "init_db.py --reset aborts when typed confirmation does not match" {
  run bash -c "echo 'wrong_db_name' | .venv/bin/python scripts/init_db.py --reset"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Operation cancelled" ]]
}

@test "migrate_legacy.py --clear blocks in production environment without ALLOW_PROD_CLEAR" {
  local mock_json="${TEST_TEMP_DIR}/data.json"
  echo '{"manifestations": []}' > "${mock_json}"

  FLASK_ENV=production run .venv/bin/python scripts/migrate_legacy.py "${mock_json}" --clear
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Refusing to clear database in production environment" ]]
}

@test "migrate_legacy.py --clear aborts when typed confirmation does not match" {
  local mock_json="${TEST_TEMP_DIR}/data.json"
  echo '{"manifestations": []}' > "${mock_json}"

  run bash -c "echo 'wrong_db_name' | .venv/bin/python scripts/migrate_legacy.py '${mock_json}' --clear"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Operation cancelled" ]]
}
