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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "verify_federation_preview.sh displays help information with --help and -h" {
  run bash scripts/verify_federation_preview.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Usage: ./scripts/verify_federation_preview.sh" ]]
  [[ "$output" =~ "--seed-only" ]]
  [[ "$output" =~ "--timeout" ]]

  run bash scripts/verify_federation_preview.sh -h
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Usage: ./scripts/verify_federation_preview.sh" ]]
}

@test "verify_federation_preview.sh rejects unknown CLI arguments" {
  run bash scripts/verify_federation_preview.sh --unknown-foo-flag
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Unknown option: --unknown-foo-flag" ]]
}

@test "verify_federation_preview.sh validates --timeout parameter" {
  run bash scripts/verify_federation_preview.sh --timeout
  [ "$status" -eq 1 ]
  [[ "$output" =~ "--timeout requires an integer argument" ]]

  run bash scripts/verify_federation_preview.sh --timeout notanumber
  [ "$status" -eq 1 ]
  [[ "$output" =~ "--timeout requires an integer argument" ]]
}

@test "verify_federation_preview.sh suppresses banners and info in quiet mode" {
  # Mock docker to simulate missing containers and fail fast
  mkdir -p "${TEST_TEMP_DIR}/bin"
  cat << 'EOF' > "${TEST_TEMP_DIR}/bin/docker"
#!/bin/sh
exit 1
EOF
  chmod +x "${TEST_TEMP_DIR}/bin/docker"

  run env PATH="${TEST_TEMP_DIR}/bin:$PATH" bash scripts/verify_federation_preview.sh --quiet
  [ "$status" -eq 1 ]
  [[ ! "$output" =~ "============================================================" ]]
  [[ ! "$output" =~ "[INFO]" ]]
}

@test "verify_federation_preview.sh fails when primary container is offline" {
  mkdir -p "${TEST_TEMP_DIR}/bin"
  cat << 'EOF' > "${TEST_TEMP_DIR}/bin/docker"
#!/bin/sh
if [ "$1" = "ps" ]; then
  echo "other-container-1"
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/bin/docker"

  run env PATH="${TEST_TEMP_DIR}/bin:$PATH" bash scripts/verify_federation_preview.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Primary web container (iqoqo-preview-web-1) is not running" ]]
}

@test "verify_federation_preview.sh fails when peer container is offline" {
  mkdir -p "${TEST_TEMP_DIR}/bin"
  cat << 'EOF' > "${TEST_TEMP_DIR}/bin/docker"
#!/bin/sh
if [ "$1" = "ps" ]; then
  echo "iqoqo-preview-web-1"
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/bin/docker"

  run env PATH="${TEST_TEMP_DIR}/bin:$PATH" bash scripts/verify_federation_preview.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Secondary peer web container (iqoqo-preview-peer-web-1) is not running" ]]
}
