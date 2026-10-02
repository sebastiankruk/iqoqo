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
# The cron installer takes an optional rclone remote, exactly as it always has.
# The property under test is that `install` and the nightly job can never
# disagree about which backend is in use: installing for rclone while the job
# silently runs against S3 (or the reverse) is how a backup appears to be
# scheduled and then is not.

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  export PATH="${TEST_TEMP_DIR}/stub-bin:${PATH}"
  mkdir -p "${TEST_TEMP_DIR}/stub-bin"

  # Stub rclone, reporting whichever remotes the test asks for.
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
if [[ "$*" == *"listremotes"* ]]; then
  echo "${RCLONE_REMOTES:-my-remote:}"
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  # Stub docker. It echoes stdin as well as its arguments, because the cron line
  # is piped in on stdin -- without that, a test cannot see what was installed.
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [ ! -t 0 ]; then
  cat | sed 's/^/CRON_FILE_CONTENT: /'
fi
echo "DOCKER_CALLED_WITH: $*"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  # A project-shaped tree with a writable .env, since the script resolves
  # PROJECT_DIR from its own location.
  export FAKE_PROJECT="${TEST_TEMP_DIR}/project"
  mkdir -p "${FAKE_PROJECT}/scripts"
  cp scripts/cloud_backup_cron.sh "${FAKE_PROJECT}/scripts/"
  cp scripts/cloud_backup.sh "${FAKE_PROJECT}/scripts/"

  export HOME="${TEST_TEMP_DIR}/home"
  mkdir -p "${HOME}/.config/rclone"
  printf '[my-remote]\ntype = s3\n' > "${HOME}/.config/rclone/rclone.conf"

  export AWS_ACCESS_KEY_ID="AKIAEXAMPLE"
  export AWS_SECRET_ACCESS_KEY="example-secret"
  export S3_BUCKET_BACKUP="my-bucket"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "cloud_backup_cron.sh requires a command argument" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "cloud_backup_cron.sh install fails if the named remote does not exist" {
  export RCLONE_REMOTES="other-remote:"

  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install non-existent-remote
  [ "$status" -eq 1 ]
  [[ "$output" =~ "ERROR: Remote 'non-existent-remote' not found" ]]
  [[ "$output" =~ "rclone listremotes" ]]
}

@test "cloud_backup_cron.sh install succeeds and invokes docker" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Installing daily 03:00 cron job (backend: rclone, remote: my-remote)" ]]
  [[ "$output" =~ "DOCKER_CALLED_WITH: run --rm -i -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine" ]]
}

@test "cloud_backup_cron.sh passes the remote through to the cron command" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install my-remote
  [ "$status" -eq 0 ]
  # The cron line the installer writes must name the same remote it validated,
  # otherwise the 03:00 job would resolve a different destination.
  grep -q "CRON_FILE_CONTENT: 0 3 \* \* \* root cd .* && ./scripts/cloud_backup.sh my-remote " <<< "$output"
}

@test "cloud_backup_cron.sh uses the default remote when none is named" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: rclone" ]]
  # No argument is appended, so cloud_backup.sh resolves RCLONE_REMOTE_FAST itself.
  grep -q "CRON_FILE_CONTENT: 0 3 \* \* \* root cd .* && ./scripts/cloud_backup.sh " <<< "$output"
  [[ ! "$output" =~ "cloud_backup.sh my-remote" ]]
}

@test "cloud_backup_cron.sh honours RCLONE_REMOTE_FAST" {
  export RCLONE_REMOTE_FAST="my-remote"
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 0 ]
  [[ "$output" =~ "remote: my-remote" ]]
}

@test "cloud_backup_cron.sh supports the S3 backend" {
  export S3_BACKEND="s3"

  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: s3, bucket: my-bucket" ]]
  # Under S3 the variables in .env are the configuration; passing an argument
  # here would flip cloud_backup.sh back to rclone at 03:00.
  grep -q "CRON_FILE_CONTENT: 0 3 \* \* \* root cd .* && ./scripts/cloud_backup.sh " <<< "$output"
  [[ ! "$output" =~ "cloud_backup.sh my-remote" ]]
}

@test "cloud_backup_cron.sh never emits RCLONE_CONFIG in the cron command" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install my-remote
  [ "$status" -eq 0 ]
  [[ ! "$output" =~ "RCLONE_CONFIG" ]]
}

@test "cloud_backup_cron.sh install fails when S3 is selected but S3_BUCKET_BACKUP is unset" {
  export S3_BACKEND="s3"
  unset S3_BUCKET_BACKUP

  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 1 ]
  [[ "$output" =~ "S3_BUCKET_BACKUP is not set" ]]
  # No cron job may be installed when the backup could never succeed.
  [[ ! "$output" =~ "Installing daily" ]]
}

@test "cloud_backup_cron.sh install fails when S3 is selected but credentials are missing" {
  export S3_BACKEND="s3"
  unset AWS_SECRET_ACCESS_KEY

  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 1 ]
  [[ "$output" =~ "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY" ]]
  [[ ! "$output" =~ "Installing daily" ]]
}

@test "cloud_backup_cron.sh install fails when nothing is configured" {
  rm -f "${HOME}/.config/rclone/rclone.conf"
  unset S3_BUCKET_BACKUP AWS_ACCESS_KEY_ID

  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 1 ]
  [[ "$output" =~ "no backup destination is configured" ]]
  [[ ! "$output" =~ "Installing daily" ]]
}

@test "cloud_backup_cron.sh rejects an unknown S3_BACKEND" {
  export S3_BACKEND="gcs"

  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" install
  [ "$status" -eq 1 ]
  [[ "$output" =~ "S3_BACKEND must be one of: auto, rclone, s3" ]]
}

@test "cloud_backup_cron.sh uninstall invokes docker removal" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" uninstall
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Removing iQoQo backup cron job" ]]
  [[ "$output" =~ "DOCKER_CALLED_WITH: run --rm -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c rm -f /etc/cron.d/iqoqo-backup" ]]
}

@test "cloud_backup_cron.sh archive-install succeeds and invokes docker" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" archive-install my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Installing monthly 04:00 cron job (backend: rclone, remote: my-remote)" ]]
  [[ "$output" =~ "DOCKER_CALLED_WITH: run --rm -i -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine" ]]
  grep -q "CRON_FILE_CONTENT: 0 4 1 \* \* root cd .* && ./scripts/cloud_backup.sh my-remote " <<< "$output"
}

@test "cloud_backup_cron.sh archive-uninstall invokes docker removal" {
  run bash "${FAKE_PROJECT}/scripts/cloud_backup_cron.sh" archive-uninstall
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Removing iQoQo archive cron job" ]]
  [[ "$output" =~ "DOCKER_CALLED_WITH: run --rm -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c rm -f /etc/cron.d/iqoqo-archive" ]]
}
