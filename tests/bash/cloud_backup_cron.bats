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

  # Stub rclone
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
if [[ "$*" == *"listremotes"* ]]; then
  echo "my-remote:"
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  # Stub docker
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
echo "DOCKER_CALLED_WITH: $*"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "cloud_backup_cron.sh requires argument" {
  run bash scripts/cloud_backup_cron.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "cloud_backup_cron.sh install fails if remote is missing in rclone" {
  run bash scripts/cloud_backup_cron.sh install non-existent-remote
  [ "$status" -eq 1 ]
  [[ "$output" =~ "ERROR: Remote 'non-existent-remote' not found" ]]
}

@test "cloud_backup_cron.sh install succeeds and invokes docker for cron configuration" {
  run bash scripts/cloud_backup_cron.sh install my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Installing daily 03:00 cron job for remote 'my-remote'" ]]
  [[ "$output" =~ "DOCKER_CALLED_WITH: run --rm -i -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine" ]]
}

@test "cloud_backup_cron.sh uninstall invokes docker removal" {
  run bash scripts/cloud_backup_cron.sh uninstall
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Removing iQoQo backup cron job" ]]
  [[ "$output" =~ "DOCKER_CALLED_WITH: run --rm -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c rm -f /etc/cron.d/iqoqo-backup" ]]
}
