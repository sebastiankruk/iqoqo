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
# Tests for deploy/docker-entrypoint.sh pre-start rclone directory check
# (OpenSpec v0716-alembic-migration-sre, task 3.3).
#
# Verifies:
#   - rclone config dir is created when absent (fresh container deployment)
#   - check is idempotent: re-running does not fail when dir already exists
#   - entrypoint exec's the given command and propagates its exit code

ENTRYPOINT="${BATS_TEST_DIRNAME}/../../deploy/docker-entrypoint.sh"

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  # Override HOME so mkdir -p targets our temp dir, not the real one
  export HOME="${TEST_TEMP_DIR}/fakehome"
  mkdir -p "${HOME}"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "entrypoint creates rclone config dir on fresh container (dir absent)" {
  # Confirm directory is absent before running
  [ ! -d "${HOME}/.config/rclone" ]

  run bash "${ENTRYPOINT}" true

  [ "${status}" -eq 0 ]
  [ -d "${HOME}/.config/rclone" ]
}

@test "entrypoint is idempotent: does not fail when rclone dir already exists" {
  # Pre-create the directory (simulates an existing bind-mount or prior run)
  mkdir -p "${HOME}/.config/rclone"
  echo "rclone_config_placeholder = exists" > "${HOME}/.config/rclone/rclone.conf"

  run bash "${ENTRYPOINT}" true

  [ "${status}" -eq 0 ]
  # Existing file inside the directory must still be present
  [ -f "${HOME}/.config/rclone/rclone.conf" ]
}

@test "entrypoint exec's the given command and exits with its code" {
  run bash "${ENTRYPOINT}" sh -c "exit 0"
  [ "${status}" -eq 0 ]
}

@test "entrypoint propagates non-zero exit code from wrapped command" {
  run bash "${ENTRYPOINT}" sh -c "exit 42"
  [ "${status}" -eq 42 ]
}

@test "entrypoint warns when rclone.conf is not readable" {
  mkdir -p "${HOME}/.config/rclone"
  touch "${HOME}/.config/rclone/rclone.conf"
  chmod 0000 "${HOME}/.config/rclone/rclone.conf"

  # Create mock chmod to prevent chmod 0600 from making the file readable
  MOCK_BIN="${TEST_TEMP_DIR}/mock-bin"
  mkdir -p "${MOCK_BIN}"
  printf '#!/bin/sh\nexit 1\n' > "${MOCK_BIN}/chmod"
  chmod +x "${MOCK_BIN}/chmod"

  PATH="${MOCK_BIN}:${PATH}" run bash "${ENTRYPOINT}" true
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "WARNING:" ]]
  [[ "${output}" =~ "not readable" ]]
}

@test "entrypoint does not warn when rclone.conf is readable" {
  mkdir -p "${HOME}/.config/rclone"
  touch "${HOME}/.config/rclone/rclone.conf"
  chmod 0600 "${HOME}/.config/rclone/rclone.conf"

  run bash "${ENTRYPOINT}" true
  [ "${status}" -eq 0 ]
  [[ ! "${output}" =~ "WARNING:" ]]
}
