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
  export PATH="${TEST_TEMP_DIR}/stub-bin:${PATH}"
  mkdir -p "${TEST_TEMP_DIR}/stub-bin"

  # Stub sudo to bypass and just execute the command directly
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/sudo"
#!/bin/bash
exec "$@"
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/sudo"

  # Stub docker
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
# Just succeed on cp, exec, etc.
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "import_covers.sh exits 1 if archive does not exist" {
  run bash scripts/import_covers.sh my-container "/nonexistent/path/covers.tar.gz"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Error: Archive not found" ]]
}

@test "import_covers.sh runs successfully when archive exists and user declines deletion" {
  # Create a dummy archive file
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  touch "${archive}"

  # Pipe 'n' to answer the delete prompt
  run bash -c "echo 'n' | bash scripts/import_covers.sh test-container ${archive}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Import complete!" ]]
  [[ "$output" =~ "Archive kept on host" ]]
  [ -f "${archive}" ]
}

@test "import_covers.sh runs successfully and deletes archive when user accepts" {
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  touch "${archive}"

  # Pipe 'y' to answer the delete prompt
  run bash -c "echo 'y' | bash scripts/import_covers.sh test-container ${archive}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Import complete!" ]]
  # The file should be deleted
  [ ! -f "${archive}" ]
}
