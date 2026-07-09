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
  
  # Stub git command
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/git"
#!/bin/bash
if [[ "$1" == "ls-files" ]]; then
  # Return our test files
  echo "${TEST_TEMP_DIR}/file_ok.py"
  echo "${TEST_TEMP_DIR}/file_no_auth.py"
  echo "${TEST_TEMP_DIR}/file_no_lic.py"
fi
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/git"

  # Create temp files
  # 1. OK file
  cat << 'EOF' > "${TEST_TEMP_DIR}/file_ok.py"
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
# GNU Affero General Public License
# Some code here
EOF

  # 2. No author signature
  cat << 'EOF' > "${TEST_TEMP_DIR}/file_no_auth.py"
# GNU Affero General Public License
# Some code here
EOF

  # 3. No license signature
  cat << 'EOF' > "${TEST_TEMP_DIR}/file_no_lic.py"
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
# Some code here
EOF
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "check_license.sh detects missing author copyright" {
  # Modify check_license.sh invocation to use our stubbed git
  # We copy the script and update the git command or just run it with modified env/PATH
  # Since git ls-files is stubbed via PATH, scripts/check_license.sh will invoke it
  run bash scripts/check_license.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Missing copyright info" ]]
}

@test "check_license.sh exits 0 when all files are compliant" {
  # Re-stub git to only return compliant files
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/git"
#!/bin/bash
if [[ "$1" == "ls-files" ]]; then
  echo "${TEST_TEMP_DIR}/file_ok.py"
fi
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/git"

  run bash scripts/check_license.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "All source files contain the correct license header" ]]
}
