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

@test "clone.sh fails if fewer than 4 arguments are provided" {
  run bash scripts/clone.sh dir1 name1 dir2
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "clone.sh fails if source directory does not exist locally" {
  run bash scripts/clone.sh "/nonexistent/src" prod "${TEST_TEMP_DIR}" preview
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Error: Source directory" ]]
}

@test "clone.sh fails if destination directory does not exist" {
  local src_dir="${TEST_TEMP_DIR}/src"
  mkdir -p "${src_dir}"
  run bash scripts/clone.sh "${src_dir}" prod "/nonexistent/dst" preview
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Error: Destination directory" ]]
}
