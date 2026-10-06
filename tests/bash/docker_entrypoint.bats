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
# Tests for deploy/docker-entrypoint.sh pre-start checks.
#
# The entrypoint no longer creates an rclone config directory — remote storage
# is configured from environment variables via boto3. What remains is a
# half-configuration check, because a bucket with no credentials (or the
# reverse) makes every remote operation silently no-op, and the first symptom
# is a backup archive that never appears. Plus the legacy-config notice and the
# exec/URL-rewrite behaviour.
#
# (Predecessor: OpenSpec v0716-alembic-migration-sre task 3.3.)

ENTRYPOINT="${BATS_TEST_DIRNAME}/../../deploy/docker-entrypoint.sh"

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  # Override HOME so the legacy-config probe targets our temp dir, not the real one
  export HOME="${TEST_TEMP_DIR}/fakehome"
  mkdir -p "${HOME}"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "entrypoint does not create an rclone config directory" {
  # The old implementation created ${HOME}/.config/rclone on every start. With
  # rclone gone there is nothing to create, and an empty credential directory is
  # exactly the kind of thing that suggests a mount is expected.
  [ ! -d "${HOME}/.config" ]

  run bash "${ENTRYPOINT}" true

  [ "${status}" -eq 0 ]
  [ ! -d "${HOME}/.config/rclone" ]
}

@test "entrypoint exec's the given command and exits with its code" {
  run bash "${ENTRYPOINT}" sh -c "exit 0"
  [ "${status}" -eq 0 ]
}

@test "entrypoint propagates non-zero exit code from wrapped command" {
  run bash "${ENTRYPOINT}" sh -c "exit 42"
  [ "${status}" -eq 42 ]
}

@test "entrypoint warns when a bucket is set but credentials are missing" {
  run env S3_BUCKET_BACKUP=my-backups bash "${ENTRYPOINT}" true
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "WARNING:" ]]
  [[ "${output}" =~ "AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY is empty" ]]
}

@test "entrypoint warns when credentials are set but no bucket is configured" {
  run env AWS_ACCESS_KEY_ID=AKIAEXAMPLE AWS_SECRET_ACCESS_KEY=secret bash "${ENTRYPOINT}" true
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "WARNING:" ]]
  [[ "${output}" =~ no.S3_BUCKET_.*.variable.is.set ]]
}

@test "entrypoint does not warn when S3 is fully configured" {
  run env AWS_ACCESS_KEY_ID=AKIAEXAMPLE AWS_SECRET_ACCESS_KEY=secret \
      S3_BUCKET_BACKUP=my-backups bash "${ENTRYPOINT}" true
  [ "${status}" -eq 0 ]
  [[ ! "${output}" =~ "WARNING:" ]]
}

@test "entrypoint does not warn when S3 is entirely absent" {
  run bash "${ENTRYPOINT}" true
  [ "${status}" -eq 0 ]
  [[ ! "${output}" =~ "WARNING:" ]]
}

@test "entrypoint reports a leftover rclone.conf so the bind-mount gets removed" {
  mkdir -p "${HOME}/.config/rclone"
  touch "${HOME}/.config/rclone/rclone.conf"

  run bash "${ENTRYPOINT}" true

  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "is no longer used" ]]
  [[ "${output}" =~ "Remove the rclone.conf bind-mount" ]]
}

@test "entrypoint survives a read-only HOME" {
  RO_HOME="${TEST_TEMP_DIR}/readonly-home"
  mkdir -p "${RO_HOME}"
  chmod 0555 "${TEST_TEMP_DIR}" "${RO_HOME}"

  run env HOME="${RO_HOME}" bash "${ENTRYPOINT}" true

  [ "${status}" -eq 0 ]

  chmod -R u+rwX "${TEST_TEMP_DIR}" 2>/dev/null || true
}

@test "entrypoint rewrites localhost database and redis URLs to docker service names" {
  DATABASE_URL="postgresql://iqoqo:pass@localhost:5432/iqoqo" \
  REDIS_URL="redis://localhost:6379/0" \
  run bash "${ENTRYPOINT}" sh -c 'echo "DB=$DATABASE_URL REDIS=$REDIS_URL"'
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "DB=postgresql://iqoqo:pass@db:5432/iqoqo" ]]
  [[ "${output}" =~ "REDIS=redis://redis:6379/0" ]]
}

@test "entrypoint rewrites 127.0.0.1 database and redis URLs to docker service names" {
  DATABASE_URL="postgresql://iqoqo:pass@127.0.0.1:5432/iqoqo" \
  REDIS_URL="redis://127.0.0.1:6379/0" \
  run bash "${ENTRYPOINT}" sh -c 'echo "DB=$DATABASE_URL REDIS=$REDIS_URL"'
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "DB=postgresql://iqoqo:pass@db:5432/iqoqo" ]]
  [[ "${output}" =~ "REDIS=redis://redis:6379/0" ]]
}

@test "entrypoint rewrites scheme-relative 127.0.0.1 URLs" {
  # The `//host:port` form is what a socket-style URL looks like; it must be
  # rewritten too, or the container silently talks to itself and fails to connect.
  DATABASE_URL="postgresql://iqoqo:pass@//127.0.0.1:5432/iqoqo" \
  run bash "${ENTRYPOINT}" sh -c 'echo "DB=$DATABASE_URL"'
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "DB=postgresql://iqoqo:pass@//db:5432/iqoqo" ]]
}

@test "entrypoint leaves an already-correct service URL untouched" {
  DATABASE_URL="postgresql://iqoqo:pass@db:5432/iqoqo" \
  REDIS_URL="redis://redis:6379/0" \
  run bash "${ENTRYPOINT}" sh -c 'echo "DB=$DATABASE_URL REDIS=$REDIS_URL"'
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "DB=postgresql://iqoqo:pass@db:5432/iqoqo" ]]
  [[ "${output}" =~ "REDIS=redis://redis:6379/0" ]]
}
