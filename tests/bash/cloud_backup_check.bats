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

  # Stub df to return plenty of space
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/df"
#!/bin/bash
echo "Filesystem 1K-blocks Used Available Use% Mounted on"
echo "/dev/sda1  100000000 1000000 99000000   1% /"
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/df"

  # Stub rclone
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
if [[ "$*" == *"listremotes"* ]]; then
  echo "my-remote:"
elif [[ "$*" == *"about"* ]]; then
  echo "Total: 1TB"
elif [[ "$*" == *"lsl"* ]]; then
  # Print dummy entry with current date
  echo "  10000000 2026-07-09 12:00:00 my_backup.tar.gz"
fi
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  # Stub date to support -d option on macOS
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/date"
#!/bin/bash
if [[ "$*" == *"-d"* ]]; then
  # Return a dynamic epoch representing 4 hours ago
  echo $(($(/bin/date +%s) - 14400))
  exit 0
fi
# Fallback to system date
/bin/date "$@"
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/date"

  # Mock cron file path in check script or environment
  # The script hardcodes: CRON_FILE="/etc/cron.d/iqoqo-backup"
  # Since we don't have write access to /etc/cron.d/ on standard test environment,
  # we should test how the script fails when it doesn't exist, OR
  # mock grep/cat if needed. But let's check its behavior.
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "cloud_backup_check.sh fails when cron file is missing" {
  TEMP_CHECK_SCRIPT="${TEST_TEMP_DIR}/check_missing_cron.sh"
  cp scripts/cloud_backup_check.sh "${TEMP_CHECK_SCRIPT}"
  sed -i.bak "s|/etc/cron.d/iqoqo-backup|${TEST_TEMP_DIR}/nonexistent-cron|g" "${TEMP_CHECK_SCRIPT}"

  run bash "${TEMP_CHECK_SCRIPT}" my-remote
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Cron job: not installed" ]]
}

@test "cloud_backup_check.sh succeeds if cron file is stubbed and all checks pass" {
  # We stub the path to the cron file by mocking check script behavior
  # Since the check script defines CRON_FILE="/etc/cron.d/iqoqo-backup", we can
  # patch the script dynamically to use a test temp cron file for this test!
  TEMP_CHECK_SCRIPT="${TEST_TEMP_DIR}/check.sh"
  cp scripts/cloud_backup_check.sh "${TEMP_CHECK_SCRIPT}"
  # Copy cloud_backup.sh because the check script runs syntax checks on it in its own dir
  cp scripts/cloud_backup.sh "${TEST_TEMP_DIR}/"
  
  # Replace "/etc/cron.d/iqoqo-backup" with our temp path
  TEMP_CRON_FILE="${TEST_TEMP_DIR}/cron-job"
  echo "* * * * * root /usr/src/app/scripts/cloud_backup.sh my-remote" > "${TEMP_CRON_FILE}"
  
  sed -i.bak "s|/etc/cron.d/iqoqo-backup|${TEMP_CRON_FILE}|g" "${TEMP_CHECK_SCRIPT}"
  
  run bash "${TEMP_CHECK_SCRIPT}" my-remote
  # Should be 0 since rclone, df, and cron are stubbed correctly
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[OK]  Cron job: references cloud_backup.sh" ]]
  [[ "$output" =~ "[OK]  Rclone remote 'my-remote': configured" ]]
  [[ "$output" =~ "All checks passed!" ]]
}
