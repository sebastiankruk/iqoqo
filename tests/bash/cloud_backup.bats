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

  # Stub rclone to do nothing and exit 0
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  # Stub docker to simulate database pg_dumpall
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"exec"* ]] && [[ "$*" == *"pg_dumpall"* ]]; then
  echo "CREATE TABLE test;"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "cloud_backup.sh exits 0 on successful backup and copy" {
  run bash scripts/cloud_backup.sh my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Backup completed successfully" ]]
}

@test "cloud_backup.sh fails if postgres dump is empty" {
  # Re-stub docker to produce no output (empty dump)
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash scripts/cloud_backup.sh my-remote
  [ "$status" -eq 1 ]
  [[ "$output" =~ "PostgreSQL dump is empty" ]]
}

@test "cloud_backup.sh uses custom remote name" {
  # Capture the arguments sent to rclone
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
echo "RCLONE_CALLED_WITH: $*"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  run bash scripts/cloud_backup.sh custom-remote-name
  [ "$status" -eq 0 ]
  [[ "$output" =~ "RCLONE_CALLED_WITH: copy" ]]
  [[ "$output" =~ "custom-remote-name:iqoqo_backups" ]]
}

@test "cloud_backup.sh respects full remote:bucket target syntax" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
echo "RCLONE_CALLED_WITH: $*"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  run bash scripts/cloud_backup.sh "custom-remote:custom-bucket"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "RCLONE_CALLED_WITH: copy" ]]
  [[ "$output" =~ "custom-remote:custom-bucket" ]]
}

@test "cloud_backup.sh creates ~/.config/rclone dir before running rclone" {
  export HOME="${TEST_TEMP_DIR}/home"
  
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
if [ -d "$HOME/.config/rclone" ]; then
  echo "RCLONE_DIR_EXISTS"
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  run bash scripts/cloud_backup.sh dummy-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "RCLONE_DIR_EXISTS" ]]
}

@test "cloud_backup.sh uses POSIX -- delimiters for rclone" {
  export HOME="${TEST_TEMP_DIR}/home"
  
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
echo "RCLONE_ARGS: $*"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  run bash scripts/cloud_backup.sh dummy-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ " -- " ]]
}
