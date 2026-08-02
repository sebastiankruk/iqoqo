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

  # Default docker stub: volume exists, no containers using it
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
case "$1" in
  volume)
    case "$2" in
      inspect)
        # Fail for backup volumes, succeed for source volumes
        if [[ "$3" == *"_v16_backup"* ]]; then
          exit 1
        fi
        exit 0
        ;;
      create|rm)
        exit 0
        ;;
    esac
    ;;
  ps)
    # No containers using volume
    echo ""
    exit 0
    ;;
  pull)
    exit 0
    ;;
  run)
    exit 0
    ;;
  exec)
    # Simulate pg_isready success
    if [[ "$*" == *"pg_isready"* ]]; then
      exit 0
    fi
    # Simulate pg_dumpall success
    if [[ "$*" == *"pg_dumpall"* ]]; then
      echo "-- PostgreSQL dump"
      exit 0
    fi
    # Simulate psql restore success
    if [[ "$*" == *"psql"* ]]; then
      exit 0
    fi
    exit 0
    ;;
  rm)
    exit 0
    ;;
esac
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "migrate-postgres script shows help with --help" {
  run bash deploy/migrate-postgres-16-to-18.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Usage:" ]]
  [[ "$output" =~ "dev | preview | prod" ]]
}

@test "migrate-postgres script fails without stack argument" {
  run bash deploy/migrate-postgres-16-to-18.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Stack name required" ]]
}

@test "migrate-postgres script fails with unknown stack" {
  run bash deploy/migrate-postgres-16-to-18.sh staging
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Unknown argument" ]]
}

@test "migrate-postgres script resolves prod volume name correctly" {
  run bash deploy/migrate-postgres-16-to-18.sh prod --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "iqoqo_postgres_data" ]]
}

@test "migrate-postgres script resolves preview volume name correctly" {
  run bash deploy/migrate-postgres-16-to-18.sh preview --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "iqoqo-preview_postgres_data" ]]
}

@test "migrate-postgres script resolves dev volume name correctly" {
  run bash deploy/migrate-postgres-16-to-18.sh dev --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "iqoqo-dev_postgres_data" ]]
}

@test "migrate-postgres dry run shows all steps without executing" {
  run bash deploy/migrate-postgres-16-to-18.sh prod --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY RUN" ]]
  [[ "$output" =~ "postgres:16-alpine" ]]
  [[ "$output" =~ "postgres:18-alpine" ]]
  [[ "$output" =~ "iqoqo_postgres_data" ]]
  [[ "$output" =~ "iqoqo_postgres_data_v16_backup" ]]
}

@test "migrate-postgres dry run shows rollback instructions" {
  run bash deploy/migrate-postgres-16-to-18.sh prod --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "roll back" ]]
}

@test "migrate-postgres fails when volume does not exist" {
  # Override docker stub so volume inspect fails for everything
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$1" == "volume" ]] && [[ "$2" == "inspect" ]]; then
  exit 1
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash deploy/migrate-postgres-16-to-18.sh prod
  [ "$status" -eq 1 ]
  [[ "$output" =~ "does not exist" ]]
}

@test "migrate-postgres fails when containers are using the volume" {
  # Override docker stub so ps returns a container ID
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$1" == "volume" ]] && [[ "$2" == "inspect" ]]; then
  if [[ "$3" == *"_v16_backup"* ]]; then
    exit 1
  fi
  exit 0
fi
if [[ "$1" == "ps" ]]; then
  echo "abc123def456"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash deploy/migrate-postgres-16-to-18.sh prod
  [ "$status" -eq 1 ]
  [[ "$output" =~ "in use" ]]
}

@test "migrate-postgres script is executable" {
  [ -x "deploy/migrate-postgres-16-to-18.sh" ]
}
