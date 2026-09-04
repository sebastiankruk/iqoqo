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

  # Stub docker build
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$1" == "build" ]]; then
  echo "BUILDING_DOCKER_IMAGE: $*"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  # Copy pyproject.toml to the temp dir to run the test in isolation
  cp pyproject.toml "${TEST_TEMP_DIR}/"
  mkdir -p "${TEST_TEMP_DIR}/deploy"
  if [ -f deploy/Dockerfile ]; then
    cp deploy/Dockerfile "${TEST_TEMP_DIR}/deploy/"
  else
    touch "${TEST_TEMP_DIR}/deploy/Dockerfile"
  fi
  if [ -f deploy/Dockerfile.nginx ]; then
    cp deploy/Dockerfile.nginx "${TEST_TEMP_DIR}/deploy/"
  else
    touch "${TEST_TEMP_DIR}/deploy/Dockerfile.nginx"
  fi
  mkdir -p "${TEST_TEMP_DIR}/frontend"
  touch "${TEST_TEMP_DIR}/frontend/Dockerfile.prod"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "test_docker_builds.sh executes build commands successfully" {
  # Run the script in the context of the temp dir
  cd "${TEST_TEMP_DIR}"
  run bash "${BATS_TEST_DIRNAME}/../../scripts/test_docker_builds.sh"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Extracting version from pyproject.toml" ]]
  [[ "$output" =~ "BUILDING_DOCKER_IMAGE: build -t iqoqo-backend:" ]]
  [[ "$output" =~ "BUILDING_DOCKER_IMAGE: build -t iqoqo-frontend:" ]]
  [[ "$output" =~ "BUILDING_DOCKER_IMAGE: build -t iqoqo-nginx:" ]]
}

@test "build_docker_images.sh builds backend, frontend, and nginx with custom tag" {
  cd "${TEST_TEMP_DIR}"
  run bash "${BATS_TEST_DIRNAME}/../../scripts/build_docker_images.sh" --tag preview
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Primary Tag: preview" ]]
  [[ "$output" =~ "BUILDING_DOCKER_IMAGE: build" ]]
  [[ "$output" =~ "iqoqo-backend:preview" ]]
  [[ "$output" =~ "iqoqo-frontend:preview" ]]
  [[ "$output" =~ "iqoqo-nginx:preview" ]]
}
