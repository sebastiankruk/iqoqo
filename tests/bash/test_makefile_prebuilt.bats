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
# tests/bash/test_makefile_prebuilt.bats
# Tests for Makefile prebuilt deployment targets without host Python/Node dependencies.

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  export MOCK_BIN="${TEST_TEMP_DIR}/mock-bin"
  mkdir -p "${MOCK_BIN}"

  # Create mock docker binary that logs all invocations
  cat << 'DOCKER_EOF' > "${MOCK_BIN}/docker"
#!/bin/bash
echo "DOCKER_INVOCATION: $*" >> "${TEST_TEMP_DIR}/docker.log"
if [[ "$*" == *"compose"* ]] && [[ "$*" == *"config"* ]]; then
  echo "name: test"
  exit 0
fi
exit 0
DOCKER_EOF
  chmod +x "${MOCK_BIN}/docker"

  # Create poison binaries for python, python3, node, npm to guarantee they are never called
  cat << 'POISON_EOF' > "${MOCK_BIN}/python"
#!/bin/bash
echo "POISON: python was called!" >&2
exit 101
POISON_EOF
  chmod +x "${MOCK_BIN}/python"

  cat << 'POISON_EOF' > "${MOCK_BIN}/python3"
#!/bin/bash
echo "POISON: python3 was called!" >&2
exit 102
POISON_EOF
  chmod +x "${MOCK_BIN}/python3"

  cat << 'POISON_EOF' > "${MOCK_BIN}/node"
#!/bin/bash
echo "POISON: node was called!" >&2
exit 103
POISON_EOF
  chmod +x "${MOCK_BIN}/node"

  cat << 'POISON_EOF' > "${MOCK_BIN}/npm"
#!/bin/bash
echo "POISON: npm was called!" >&2
exit 104
POISON_EOF
  chmod +x "${MOCK_BIN}/npm"

  export PATH="${MOCK_BIN}:/usr/bin:/bin"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "make prod start prebuilt executes without host python or node" {
  run make prod start prebuilt
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Deploying iqoqo (prebuilt)..." ]]
  [[ "$output" =~ "Project version:" ]]
  [[ "$output" =~ "Prebuilt tag: prod" ]]

  # Verify docker commands were executed
  [ -f "${TEST_TEMP_DIR}/docker.log" ]
  run cat "${TEST_TEMP_DIR}/docker.log"
  [[ "$output" =~ "image prune -f --filter dangling=true" ]]
  [[ "$output" =~ "compose" ]]
  [[ "$output" =~ "-f docker-compose.prebuilt.yml pull" ]]
  [[ "$output" =~ "-f docker-compose.prebuilt.yml up -d" ]]
}

@test "make preview start prebuilt executes without host python or node" {
  run make preview start prebuilt
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Deploying iqoqo-preview (prebuilt)..." ]]
  [[ "$output" =~ "Project version:" ]]
  [[ "$output" =~ "Prebuilt tag: preview" ]]

  [ -f "${TEST_TEMP_DIR}/docker.log" ]
  run cat "${TEST_TEMP_DIR}/docker.log"
  [[ "$output" =~ "image prune -f --filter dangling=true" ]]
  [[ "$output" =~ "-f docker-compose.prebuilt.yml pull" ]]
  [[ "$output" =~ "-f docker-compose.prebuilt.yml up -d" ]]
}

@test "make version displays project and prebuilt versions" {
  run make version
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Project version:" ]]
  [[ "$output" =~ "Prebuilt tag:" ]]
}

@test "make prod start prebuilt respects custom APP_VERSION" {
  run env APP_VERSION="v0.7.17-custom" make prod start prebuilt
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Prebuilt tag: v0.7.17-custom" ]]
}
