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

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  export DEPLOY_DIR="${TEST_TEMP_DIR}/deploy"
  mkdir -p "${DEPLOY_DIR}"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

# ── Status and Deployment Dir Env Resolution ─────────────────────────────────

@test "iqoqo-status.sh --deploy-dir fails immediately when deployment .env is missing" {
  run bash scripts/iqoqo-status.sh --deploy-dir "${TEST_TEMP_DIR}/nonexistent"
  [ "$status" -eq 2 ]
  [[ "$output" =~ "Deployment env file not found" ]]
}

@test "iqoqo-status.sh and deploy path resolve the exact same deployment env file" {
  cat << 'EOF' > "${DEPLOY_DIR}/.env"
MODE=preview
COMPOSE_PROJECT_NAME=iqoqo-preview
DB_PORT=5499
REDIS_PORT=6399
NEXT_PUBLIC_APP_URL=https://custom.iqoqo.cc
NEXT_PUBLIC_FRONTEND_URL=https://custom.iqoqo.cc
EOF

  run env IQOQO_AI_MODE="" bash scripts/iqoqo-status.sh --deploy-dir "${DEPLOY_DIR}"
  # Script must attempt connecting to 5499 or report status for custom.iqoqo.cc, not localhost
  [[ "$output" =~ "custom.iqoqo.cc" ]]
}

# ── Mount Pre-flight and Validation ──────────────────────────────────────────

@test "pre_deploy_mounts.py creates missing directories as app user and tightens permissions" {
  echo "SECRET_KEY=test" > "${DEPLOY_DIR}/.env"
  chmod 0644 "${DEPLOY_DIR}/.env"

  run python3 scripts/pre_deploy_mounts.py "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]

  # .env tightened to 0600
  env_mode=$(stat -c '%a' "${DEPLOY_DIR}/.env" 2>/dev/null || stat -f '%p' "${DEPLOY_DIR}/.env")
  [[ "$env_mode" =~ 600$ ]]

  # .allegro_token.json created as regular file
  [ -f "${DEPLOY_DIR}/.allegro_token.json" ]
  [ ! -d "${DEPLOY_DIR}/.allegro_token.json" ]

  # Directories created with app user ownership
  current_user=$(id -u)
  dir_owner=$(stat -c '%u' "${DEPLOY_DIR}/data")
  [ "$dir_owner" -eq "$current_user" ]
  [ -d "${DEPLOY_DIR}/docs/ontology" ]
  [ -d "${DEPLOY_DIR}/app/static/covers" ]
}

@test "pre_deploy_mounts.py replaces empty directory .allegro_token.json with regular file" {
  mkdir -p "${DEPLOY_DIR}/.allegro_token.json"
  [ -d "${DEPLOY_DIR}/.allegro_token.json" ]

  run python3 scripts/pre_deploy_mounts.py "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]
  [ -f "${DEPLOY_DIR}/.allegro_token.json" ]
  [ ! -d "${DEPLOY_DIR}/.allegro_token.json" ]
}

@test "validate_deploy_dir.py rejects external symlinks and file-target directory mounts" {
  mkdir -p "${DEPLOY_DIR}/scripts" "${DEPLOY_DIR}/deploy"
  touch "${DEPLOY_DIR}/.env" "${DEPLOY_DIR}/docker-compose.yml"
  touch "${DEPLOY_DIR}/deploy/nginx.conf"

  # Create an external symlink
  external_dir="${TEST_TEMP_DIR}/external"
  mkdir -p "${external_dir}"
  rm -rf "${DEPLOY_DIR}/scripts"
  ln -s "${external_dir}" "${DEPLOY_DIR}/scripts"

  # Make .allegro_token.json a directory
  mkdir -p "${DEPLOY_DIR}/.allegro_token.json"

  run python3 scripts/validate_deploy_dir.py "${DEPLOY_DIR}"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "External Symlink Escaping Deployment Directory" ]]
  [[ "$output" =~ "Invalid File-Target Mount Type" ]]
}

@test "validate_deploy_dir.py accepts intra-directory symlinks" {
  mkdir -p "${DEPLOY_DIR}/real_scripts" "${DEPLOY_DIR}/deploy"
  touch "${DEPLOY_DIR}/.env" "${DEPLOY_DIR}/docker-compose.yml"
  touch "${DEPLOY_DIR}/deploy/nginx.conf"
  touch "${DEPLOY_DIR}/.allegro_token.json"

  ln -s "${DEPLOY_DIR}/real_scripts" "${DEPLOY_DIR}/scripts"

  run python3 scripts/validate_deploy_dir.py "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "0 violations found" ]]
}

# ── Full Self-contained Deployment Sync ──────────────────────────────────────

@test "sync_deploy_dir.py materialises self-contained deployment directory" {
  echo "TEST_ENV=1" > "${DEPLOY_DIR}/.env"

  run python3 scripts/sync_deploy_dir.py . "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]

  # Assert compose and runtime files exist as real files, not symlinks
  [ -f "${DEPLOY_DIR}/docker-compose.yml" ]
  [ ! -L "${DEPLOY_DIR}/docker-compose.yml" ]
  [ -f "${DEPLOY_DIR}/Makefile" ]
  [ ! -L "${DEPLOY_DIR}/Makefile" ]
  [ -f "${DEPLOY_DIR}/deploy/nginx.conf" ]
  [ ! -L "${DEPLOY_DIR}/deploy/nginx.conf" ]
  [ -d "${DEPLOY_DIR}/docs/ontology" ]
  [ ! -L "${DEPLOY_DIR}/docs/ontology" ]

  # Pre-deploy mounts pass
  run python3 scripts/pre_deploy_mounts.py "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]

  # Directory validator passes with 0 violations
  run python3 scripts/validate_deploy_dir.py "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]

  # Drift verify passes
  run python3 scripts/sync_deploy_dir.py --verify "${DEPLOY_DIR}"
  [ "$status" -eq 0 ]
}
