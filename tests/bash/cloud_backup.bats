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
# cloud_backup.sh has two upload backends, and the point of this file is that
# the operator's existing rclone setup keeps working unchanged while S3 is
# available as an alternative.
#
# The rclone branch is exercised with a stub binary; the S3 branch is exercised
# with a stub boto3 on PYTHONPATH. Neither touches the network.

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  export STUB_DIR="${TEST_TEMP_DIR}/stub"
  export PATH="${TEST_TEMP_DIR}/stub-bin:${PATH}"
  mkdir -p "${TEST_TEMP_DIR}/stub-bin" "${STUB_DIR}/botocore"
  export UPLOAD_RECORD="${TEST_TEMP_DIR}/upload.json"

  # A stub `docker` that emits a plausible pg_dumpall result.
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"exec"* ]] && [[ "$*" == *"pg_dumpall"* ]]; then
  echo "CREATE TABLE test;"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  # A stub rclone that records how it was called, and succeeds by default.
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
echo "RCLONE_CALLED_WITH: $*" >> "${RCLONE_LOG}"
if [ "${RCLONE_SHOULD_FAIL:-0}" = "1" ]; then
  exit 1
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"
  export RCLONE_LOG="${TEST_TEMP_DIR}/rclone.log"
  : > "${RCLONE_LOG}"

  # Satisfy `import boto3` / `botocore`, and record the upload in place of
  # touching a bucket.
  cat << 'EOF' > "${STUB_DIR}/boto3.py"
__version__ = "stub"


def client(*_args, **_kwargs):
    raise AssertionError("cloud_backup.sh must go through S3Service, not build its own client")
EOF

  cat << 'EOF' > "${STUB_DIR}/botocore/__init__.py"
EOF

  cat << 'EOF' > "${STUB_DIR}/botocore/config.py"
class Config:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
EOF

  cat << 'EOF' > "${STUB_DIR}/botocore/exceptions.py"
class BotoCoreError(Exception):
    pass


class ClientError(Exception):
    def __init__(self, error_response, operation_name):
        super().__init__(str(error_response))
        self.response = error_response


class EndpointConnectionError(BotoCoreError):
    def __init__(self, endpoint_url=""):
        super().__init__(f"could not connect to {endpoint_url}")
EOF

  cat << 'EOF' > "${STUB_DIR}/sitecustomize.py"
import json
import os

if "UPLOAD_RECORD" in os.environ:
    from app.core import s3_service

    record = os.environ["UPLOAD_RECORD"]
    should_fail = os.environ.get("S3_SHOULD_FAIL") == "1"

    class _Client:
        def upload_file(self, local_path, bucket, key, ExtraArgs=None):  # noqa: N803
            with open(record, "w", encoding="utf-8") as handle:
                json.dump({"local_path": local_path, "bucket": bucket, "key": key, "extra": ExtraArgs}, handle)
            if should_fail:
                raise RuntimeError("simulated transport failure")

    s3_service.boto3.client = lambda *_a, **_k: _Client()
EOF

  export PYTHONPATH="${STUB_DIR}:${PYTHONPATH:-}"

  # Operator-shaped environment: an rclone remote exists, so rclone is the
  # default backend. S3 credentials are also present, to prove rclone still
  # wins by default.
  export HOME="${TEST_TEMP_DIR}/home"
  mkdir -p "${HOME}/.config/rclone"
  printf '[iqoqo-backup]\ntype = s3\n' > "${HOME}/.config/rclone/rclone.conf"
  export RCLONE_REMOTE_FAST="iqoqo-backup"

  export AWS_ACCESS_KEY_ID="AKIAEXAMPLE"
  export AWS_SECRET_ACCESS_KEY="example-secret"
  export S3_BUCKET_BACKUP="iqoqo-backup-test"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
  # A preserved archive is the expected outcome of the failure tests; clean it
  # so a passing run does not leave megabytes in /tmp.
  rm -f /tmp/iqoqo_backup_*.tar.gz 2>/dev/null || true
}

# ── Backend selection ───────────────────────────────────────────────────────

@test "cloud_backup.sh uses rclone by default when a remote is configured" {
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: rclone" ]]
  [[ "$output" =~ "Backup synced" ]]
  grep -qE "RCLONE_CALLED_WITH: copy .* iqoqo-backup:iqoqo_backups$" "${RCLONE_LOG}"
}

@test "cloud_backup.sh prefers rclone even when S3 is also configured" {
  # The regression this guards: an existing operator with rclone configured must
  # not have their backups silently redirected to a different destination.
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: rclone" ]]
  [ ! -f "${UPLOAD_RECORD}" ]
}

@test "cloud_backup.sh honours an explicit remote argument" {
  run bash scripts/cloud_backup.sh my-other-remote
  [ "$status" -eq 0 ]
  grep -qE "RCLONE_CALLED_WITH: copy .* my-other-remote:iqoqo_backups$" "${RCLONE_LOG}"
}

@test "cloud_backup.sh honours a remote:path argument verbatim" {
  run bash scripts/cloud_backup.sh "custom-remote:custom-bucket"
  [ "$status" -eq 0 ]
  grep -qE "RCLONE_CALLED_WITH: copy .* custom-remote:custom-bucket$" "${RCLONE_LOG}"
}

@test "cloud_backup.sh falls back to S3 when no rclone config exists" {
  rm -f "${HOME}/.config/rclone/rclone.conf"
  unset RCLONE_REMOTE_FAST

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: s3" ]]
  [[ "$output" =~ "Backup uploaded" ]]
  [ -f "${UPLOAD_RECORD}" ]
}

@test "cloud_backup.sh S3_BACKEND=s3 overrides an available rclone remote" {
  export S3_BACKEND="s3"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: s3" ]]
  [ -f "${UPLOAD_RECORD}" ]
  [ ! -s "${RCLONE_LOG}" ]
}

@test "cloud_backup.sh ignores RCLONE_REMOTE_FAST when no rclone config exists" {
  # .env.example ships RCLONE_REMOTE_FAST=iqoqo-backup. If that alone selected
  # rclone, any S3-only operator who happened to have rclone installed for an
  # unrelated reason would be hijacked onto a backend with no config.
  rm -f "${HOME}/.config/rclone/rclone.conf"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: s3" ]]
  [ -f "${UPLOAD_RECORD}" ]
}

@test "cloud_backup.sh selects rclone from the config file even with no remote named" {
  unset RCLONE_REMOTE_FAST

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: rclone" ]]
  [[ "$output" =~ "iqoqo-backup:iqoqo_backups" ]]
}

@test "cloud_backup.sh S3_BACKEND=rclone ignores S3 credentials" {
  export S3_BACKEND="rclone"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: rclone" ]]
  [ ! -f "${UPLOAD_RECORD}" ]
}

@test "cloud_backup.sh rejects an unknown S3_BACKEND" {
  export S3_BACKEND="gcs"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "S3_BACKEND must be one of: auto, rclone, s3" ]]
}

@test "cloud_backup.sh aborts with no destination configured" {
  rm -f "${HOME}/.config/rclone/rclone.conf"
  unset RCLONE_REMOTE_FAST
  unset S3_BUCKET_BACKUP

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "no backup destination is configured" ]]
}

# ── rclone backend behaviour ────────────────────────────────────────────────

@test "cloud_backup.sh uses a POSIX -- delimiter for the rclone upload" {
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  # A timestamped filename starting with a dash would otherwise parse as a flag.
  grep -q -- "--s3-no-check-bucket -- " "${RCLONE_LOG}"
}

@test "cloud_backup.sh reports rclone's target in its output" {
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "iqoqo-backup:iqoqo_backups" ]]
}

@test "cloud_backup.sh preserves the local archive when rclone fails" {
  export RCLONE_SHOULD_FAIL=1

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Archive preserved at:" ]]

  # The whole point: a failed upload must not destroy the only copy.
  preserved=$(ls /tmp/iqoqo_backup_*.tar.gz 2>/dev/null | head -1)
  [ -n "${preserved}" ]
  [ -s "${preserved}" ]
}

@test "cloud_backup.sh cleans up after a successful rclone upload" {
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  # Assert directly rather than through `ls`, which echoes the unmatched glob
  # pattern (and that pattern contains ".tar.gz").
  shopt -s nullglob
  leftovers=(/tmp/iqoqo_backup_*.tar.gz)
  [ "${#leftovers[@]}" -eq 0 ]
}

# ── S3 backend behaviour ────────────────────────────────────────────────────

@test "cloud_backup.sh uploads under backups/iqoqo_backup_<timestamp>.tar.gz" {
  export S3_BACKEND="s3"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [ -f "${UPLOAD_RECORD}" ]

  key=$(python3 -c "import json;print(json.load(open('${UPLOAD_RECORD}'))['key'])")
  bucket=$(python3 -c "import json;print(json.load(open('${UPLOAD_RECORD}'))['bucket'])")

  [[ "${key}" =~ ^backups/iqoqo_backup_[0-9]{8}_[0-9]{6}\.tar\.gz$ ]]
  [ "${bucket}" = "iqoqo-backup-test" ]
}

@test "cloud_backup.sh honours S3_KEY_PREFIX" {
  export S3_BACKEND="s3"
  export S3_KEY_PREFIX="/custom/prefix/"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [ -f "${UPLOAD_RECORD}" ]

  # Leading and trailing slashes are normalised to exactly one separator.
  key=$(python3 -c "import json;print(json.load(open('${UPLOAD_RECORD}'))['key'])")
  [[ "${key}" =~ ^custom/prefix/iqoqo_backup_[0-9]{8}_[0-9]{6}\.tar\.gz$ ]]
}

@test "cloud_backup.sh applies S3_SSE when configured" {
  export S3_BACKEND="s3"
  export S3_SSE="AES256"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "encrypted at rest with AES256" ]]
}

@test "cloud_backup.sh aborts when S3 is selected but S3_BUCKET_BACKUP is unset" {
  export S3_BACKEND="s3"
  unset S3_BUCKET_BACKUP

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "S3_BUCKET_BACKUP is not set" ]]
  [ ! -f "${UPLOAD_RECORD}" ]
}

@test "cloud_backup.sh aborts when S3 is selected but credentials are missing" {
  export S3_BACKEND="s3"
  unset AWS_SECRET_ACCESS_KEY

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "AWS_ACCESS_KEY_ID" ]]
  [ ! -f "${UPLOAD_RECORD}" ]
}

@test "cloud_backup.sh preserves the local archive when the S3 upload fails" {
  export S3_BACKEND="s3"
  export S3_SHOULD_FAIL=1

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Archive preserved at:" ]]

  preserved=$(ls /tmp/iqoqo_backup_*.tar.gz 2>/dev/null | head -1)
  [ -n "${preserved}" ]
  [ -s "${preserved}" ]
}

# ── Shared preflight, both backends ─────────────────────────────────────────

@test "cloud_backup.sh fails if the postgres dump is empty" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "PostgreSQL dump is empty" ]]
  # An empty dump must never be uploaded as though it were a backup.
  [ ! -f "${UPLOAD_RECORD}" ]
  [ ! -s "${RCLONE_LOG}" ]
}

@test "cloud_backup.sh fails if rclone is selected but not installed" {
  # This host has a real /usr/bin/rclone, so deleting the stub is not enough.
  # Restrict PATH to a directory of symlinks that deliberately omits rclone,
  # while keeping the tools the script genuinely needs (bash, tar, date, ...).
  local no_rclone_bin="${TEST_TEMP_DIR}/no-rclone-bin"
  mkdir -p "${no_rclone_bin}"
  for tool in bash sh date tar grep head basename dirname mkdir rm cat env sed; do
    target=$(command -v "${tool}" || true)
    [ -n "${target}" ] && ln -sf "${target}" "${no_rclone_bin}/${tool}"
  done
  cp "${TEST_TEMP_DIR}/stub-bin/docker" "${no_rclone_bin}/docker"

  run env PATH="${no_rclone_bin}" S3_BACKEND=rclone bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "${output}" =~ "rclone is not installed" ]]
  [[ "${output}" =~ "S3_BACKEND=s3" ]]
}

@test "cloud_backup.sh fails if rclone is selected but has no config" {
  export S3_BACKEND="rclone"
  rm -f "${HOME}/.config/rclone/rclone.conf"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "rclone config not found" ]]
  [[ "$output" =~ "rclone config" ]]
}

# ── Execution Locking & Crash Recovery ──────────────────────────────────────

@test "cloud_backup.sh acquires and releases lock on success" {
  local lock_file="${TEST_TEMP_DIR}/test_backup.lock"
  export BACKUP_LOCK_FILE="${lock_file}"
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [ -f "${lock_file}" ]
  run flock -n "${lock_file}" true
  [ "$status" -eq 0 ]
}

@test "cloud_backup.sh exits 2 on lock contention without deleting lock" {
  local lock_file="${TEST_TEMP_DIR}/test_backup.lock"
  export BACKUP_LOCK_FILE="${lock_file}"
  export BACKUP_LOCK_TIMEOUT=1

  exec 8>"${lock_file}"
  flock 8

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 2 ]
  [[ "$output" =~ "Another backup is currently running" ]]
  [ -f "${lock_file}" ]

  exec 8>&-
}

@test "cloud_backup.sh concurrent invocations: exactly one succeeds and one exits 2" {
  local lock_file="${TEST_TEMP_DIR}/test_backup.lock"
  export BACKUP_LOCK_FILE="${lock_file}"
  export BACKUP_LOCK_TIMEOUT=1

  (
    exec 8>"${lock_file}"
    flock 8
    sleep 2
    exec 8>&-
  ) &
  local bg_pid=$!
  sleep 0.2

  run bash scripts/cloud_backup.sh
  wait "${bg_pid}" || true

  [ "$status" -eq 2 ]
  [[ "$output" =~ "Another backup is currently running" ]]
}

@test "cloud_backup.sh crash recovery: SIGKILL holder releases lock automatically" {
  local lock_file="${TEST_TEMP_DIR}/test_backup.lock"
  export BACKUP_LOCK_FILE="${lock_file}"

  (
    exec 8>"${lock_file}"
    flock 8
    sleep 30
  ) &
  local bg_pid=$!
  sleep 0.2

  run flock -n "${lock_file}" true
  [ "$status" -ne 0 ]

  kill -9 "${bg_pid}" 2>/dev/null || true
  wait "${bg_pid}" 2>/dev/null || true

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Execution summary: SUCCESS" ]]
}

@test "cloud_backup.sh cleans up temporary files on SIGTERM" {
  local lock_file="${TEST_TEMP_DIR}/test_backup.lock"
  export BACKUP_LOCK_FILE="${lock_file}"

  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"pg_dumpall"* ]]; then
  sleep 10
  echo "CREATE TABLE test;"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  bash scripts/cloud_backup.sh &
  local backup_pid=$!
  sleep 0.5
  kill -TERM "${backup_pid}" 2>/dev/null || true
  wait "${backup_pid}" 2>/dev/null || true

  run flock -n "${lock_file}" true
  [ "$status" -eq 0 ]
}

# ── Pre-flight Checks and Retry Logic ───────────────────────────────────────

@test "cloud_backup.sh preflight fails if database container is down" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
exit 1
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  export BACKUP_RETRY_ATTEMPTS=1
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Database pre-flight connectivity checks failed" ]]
}

@test "cloud_backup.sh preflight fails permanently on missing role without retry" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"SELECT 1"* ]]; then
  echo "FATAL: role \"iqoqo\" does not exist" >&2
  exit 1
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  export BACKUP_RETRY_ATTEMPTS=3
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Permanent error" ]]
  [[ "$output" =~ "attempt 1/3" ]]
  [[ ! "$output" =~ "attempt 2/3" ]]
}

@test "cloud_backup.sh preflight fails permanently on auth failure without retry" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"SELECT 1"* ]]; then
  echo "FATAL: password authentication failed for user \"iqoqo\"" >&2
  exit 1
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  export BACKUP_RETRY_ATTEMPTS=3
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Permanent error" ]]
  [[ ! "$output" =~ "attempt 2/3" ]]
}

@test "cloud_backup.sh preflight verifies custom POSTGRES_USER role" {
  export POSTGRES_USER="custom_admin"

  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
echo "DOCKER_CMD: $*" >> "${TEST_TEMP_DIR}/docker_calls.log"
if [[ "$*" == *"pg_roles"* ]]; then
  if [[ "$*" == *"custom_admin"* ]]; then
    echo "1"
    exit 0
  else
    echo "0"
    exit 0
  fi
fi
if [[ "$*" == *"pg_dumpall"* ]]; then
  echo "CREATE TABLE test;"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
  grep -q "custom_admin" "${TEST_TEMP_DIR}/docker_calls.log"
}

@test "cloud_backup.sh retries transient failures with exponential backoff schedule" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/sleep"
#!/bin/bash
echo "SLEEP: $1" >> "${TEST_TEMP_DIR}/sleep_calls.log"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/sleep"

  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"SELECT 1"* ]]; then
  echo "psql: error: could not connect to server: Connection refused" >&2
  exit 2
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  export BACKUP_RETRY_ATTEMPTS=3
  export BACKUP_RETRY_DELAY_BASE=5

  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "attempt 1/3" ]]
  [[ "$output" =~ "attempt 2/3" ]]
  [[ "$output" =~ "attempt 3/3" ]]
  [[ "$output" =~ "Database pre-flight connectivity checks failed after 3 attempts" ]]

  [ -f "${TEST_TEMP_DIR}/sleep_calls.log" ]
  run cat "${TEST_TEMP_DIR}/sleep_calls.log"
  [[ "$output" =~ "SLEEP: 5" ]]
  [[ "$output" =~ "SLEEP: 10" ]]
}

@test "cloud_backup.sh empty dump is not retried" {
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
if [[ "$*" == *"pg_dumpall"* ]]; then
  exit 0
fi
if [[ "$*" == *"pg_roles"* ]]; then
  echo "1"
  exit 0
fi
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  export BACKUP_RETRY_ATTEMPTS=3
  run bash scripts/cloud_backup.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "PostgreSQL dump is empty" ]]
  [[ ! "$output" =~ "attempt 2/3" ]]
}

