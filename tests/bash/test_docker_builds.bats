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

  PYTHON_BIN=".venv/bin/python"
  if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 || command -v python)"
  fi
  export PYTHON_BIN
  export ABS_PYTHON_BIN="$(cd "$(dirname "$PYTHON_BIN")" && pwd)/$(basename "$PYTHON_BIN")"

  # Stub docker build
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$1" == "build" ]]; then
  echo "BUILDING_DOCKER_IMAGE: $*"
  exit 0
fi
# The build script now runs the size gate against the image it just built, so
# the stub has to answer `docker image inspect` too. 1 MiB is inside any budget.
if [[ "$1" == "image" && "$2" == "inspect" ]]; then
  echo 1048576
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
  if [ -f deploy/Dockerfile.sparql ]; then
    cp deploy/Dockerfile.sparql "${TEST_TEMP_DIR}/deploy/"
  else
    touch "${TEST_TEMP_DIR}/deploy/Dockerfile.sparql"
  fi
  mkdir -p "${TEST_TEMP_DIR}/frontend"
  touch "${TEST_TEMP_DIR}/frontend/Dockerfile.prod"

  # The real gate and budget, so the happy-path tests exercise the real wiring.
  mkdir -p "${TEST_TEMP_DIR}/scripts"
  cp scripts/check_image_size.py "${TEST_TEMP_DIR}/scripts/"
  cp deploy/image-size-budget.txt "${TEST_TEMP_DIR}/deploy/"
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
  [[ "$output" =~ "BUILDING_DOCKER_IMAGE: build -t iqoqo-sparql:" ]]
}

@test "build_docker_images.sh builds backend, frontend, nginx, and sparql with custom tag and dual-tags registry prefix" {
  cd "${TEST_TEMP_DIR}"
  run bash "${BATS_TEST_DIRNAME}/../../scripts/build_docker_images.sh" --tag preview
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Primary Tag: preview" ]]
  [[ "$output" =~ "BUILDING_DOCKER_IMAGE: build" ]]
  [[ "$output" =~ "iqoqo-backend:preview" ]]
  [[ "$output" =~ "ghcr.io/sebastiankruk/iqoqo-backend:preview" ]]
  [[ "$output" =~ "iqoqo-frontend:preview" ]]
  [[ "$output" =~ "ghcr.io/sebastiankruk/iqoqo-frontend:preview" ]]
  [[ "$output" =~ "iqoqo-nginx:preview" ]]
  [[ "$output" =~ "ghcr.io/sebastiankruk/iqoqo-nginx:preview" ]]
  [[ "$output" =~ "iqoqo-sparql:preview" ]]
  [[ "$output" =~ "ghcr.io/sebastiankruk/iqoqo-sparql:preview" ]]
}

@test "build_docker_images.sh respects explicit empty prefix" {
  cd "${TEST_TEMP_DIR}"
  run bash "${BATS_TEST_DIRNAME}/../../scripts/build_docker_images.sh" --tag preview --prefix ""
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Primary Tag: preview" ]]
  [[ "$output" =~ "iqoqo-backend:preview" ]]
  [[ ! "$output" =~ "ghcr.io/sebastiankruk/iqoqo-backend:preview" ]]
}

@test "deploy/Dockerfile never bakes rclone credentials into image layers" {
  run grep -E "COPY.*rclone\.conf" "${BATS_TEST_DIRNAME}/../../deploy/Dockerfile"
  [ "$status" -ne 0 ]
}

@test "deploy/image-size-budget.txt records both enforced figures" {
  local budget="${BATS_TEST_DIRNAME}/../../deploy/image-size-budget.txt"
  # MAX_BYTES is the ceiling; MEASURED_BYTES is the measurement that justifies it.
  # A ceiling with no measurement is the old prose-requirement failure mode.
  run grep -E "^MAX_BYTES=[0-9]+$" "${budget}"
  [ "$status" -eq 0 ]
  run grep -E "^MEASURED_BYTES=[0-9]+$" "${budget}"
  [ "$status" -eq 0 ]
}

@test "the release plan quotes the enforced image size figures" {
  # Same check scripts/validate_release.py runs on release/* branches. If these
  # ever diverge, the number a release is judged against stops being the number
  # the build enforces.
  run "${ABS_PYTHON_BIN}" "${BATS_TEST_DIRNAME}/../../scripts/validate_release.py" --image-size-only
  [ "$status" -eq 0 ]
  [[ "$output" =~ "OK: image size budget" ]]
}

@test "build_docker_images.sh aborts the build when the built image is over budget" {
  # The gate must judge the real measured size, so a stubbed inspect reporting an
  # oversized image has to abort the build too. Note build_docker_images.sh
  # `cd`s to the repo root itself, so overriding files in TEST_TEMP_DIR would not
  # affect it -- the stubbed `docker` on PATH is the only lever that reaches it.
  cd "${TEST_TEMP_DIR}"
  budget="$(grep -E '^MAX_BYTES=' "${BATS_TEST_DIRNAME}/../../deploy/image-size-budget.txt" | cut -d= -f2)"
  cat << EOF > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "\$1" == "build" ]]; then echo "BUILDING_DOCKER_IMAGE: \$*"; exit 0; fi
if [[ "\$1" == "image" && "\$2" == "inspect" ]]; then echo $((budget + 1)); exit 0; fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash "${BATS_TEST_DIRNAME}/../../scripts/build_docker_images.sh" --tag preview
  [ "$status" -ne 0 ]
  [[ "$output" =~ "image size gate FAILED" ]]
  [[ "$output" =~ "EXCEEDS budget" ]]
  [[ ! "$output" =~ "All iqoqo container images built successfully" ]]
}

@test "build_docker_images.sh reports the gate result on a passing build" {
  cd "${TEST_TEMP_DIR}"
  run bash "${BATS_TEST_DIRNAME}/../../scripts/build_docker_images.sh" --tag preview
  [ "$status" -eq 0 ]
  [[ "$output" =~ "image size gate" ]]
  [[ "$output" =~ "within budget" ]]
}

@test "check_image_size.py rejects an unparseable budget instead of passing" {
  # A blank budget must fail loudly rather than read as "unlimited", which would
  # make the gate a no-op. Invoked directly because the build script always
  # resolves the real budget file relative to the repo root.
  cd "${TEST_TEMP_DIR}"
  printf '# no MAX_BYTES here\n' > broken-budget.txt
  run bash -c "'${ABS_PYTHON_BIN}' '${BATS_TEST_DIRNAME}/../../scripts/check_image_size.py' iqoqo-backend:preview --budget-file '${TEST_TEMP_DIR}/broken-budget.txt'"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "cannot read size budget" ]]
}

@test "check_image_size.py prints the size breakdown when over budget" {
  # The failure output has to name the cause, so nobody needs a second build to
  # find out what grew. Both keys are required, so the fixture supplies both.
  # The stubbed `docker` in setup() reports 1048576 bytes, so the ceiling must
  # sit below that for the gate to trip.
  cd "${TEST_TEMP_DIR}"
  printf 'MAX_BYTES=1024\nMEASURED_BYTES=1024\n' > tight-budget.txt
  run bash -c "'${ABS_PYTHON_BIN}' '${BATS_TEST_DIRNAME}/../../scripts/check_image_size.py' iqoqo-backend:preview --budget-file '${TEST_TEMP_DIR}/tight-budget.txt'"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "EXCEEDS budget" ]]
  [[ "$output" =~ "Size breakdown" ]]
}

@test "docker-compose.prebuilt.yml resets volumes on migration service" {
  run grep -A 5 "migration:" "${BATS_TEST_DIRNAME}/../../docker-compose.prebuilt.yml"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "volumes: !reset []" ]]
}


