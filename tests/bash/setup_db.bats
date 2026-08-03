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

  # We stub docker by default to report no running containers
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"ps"* ]]; then
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "setup_db.sh exits 0 with message if no running db container is found" {
  run bash scripts/setup_db.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "No running DB container found" ]]
}

@test "setup_db.sh --check reports role status when container is running" {
  # Stub docker to return a running container name
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$1" == "ps" ]]; then
  echo "iqoqo-db-1"
  exit 0
elif [[ "$1" == "exec" ]] && [[ "$*" == *"pg_roles"* ]]; then
  # Return '1' to simulate role existing
  echo "1"
  exit 0
else
  # Succeed on all other exec calls (e.g. find_superuser connectivity check)
  exit 0
fi
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash scripts/setup_db.sh --check
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Container: iqoqo-db-1" ]]
  [[ "$output" =~ Role\ \'.*\'\ EXISTS ]]
}

@test "setup_db.sh reasserts privileges if role already exists" {
  # Stub docker to return container name and simulate role exists
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$1" == "ps" ]]; then
  echo "iqoqo-db-1"
  exit 0
elif [[ "$1" == "exec" ]] && [[ "$*" == *"pg_roles"* ]]; then
  echo "1"
  exit 0
else
  # Capture sql inputs or print for assertions
  if [[ "$1" == "exec" ]] && [[ "$*" == *"psql"* ]]; then
    echo "executing psql command"
  fi
  exit 0
fi
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash scripts/setup_db.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ Role\ \'.*\'\ already\ exists\ —\ reasserting\ privileges ]]
  [[ "$output" =~ Privileges\ and\ table\ ownership\ for\ \'.*\'\ ensured. ]]
}
