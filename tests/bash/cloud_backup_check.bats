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
# The health check probes whichever backend cloud_backup.sh will actually use,
# because a green check for a destination the nightly job is not writing to is
# worse than no check at all.
#
# The rclone branch is exercised with a stub binary; the S3 branch with a stub
# boto3 on PYTHONPATH. Neither touches the network.

# Publish a single archive whose filename encodes *hours* hours ago. The S3
# branch derives freshness from that filename, so this is what the age
# assertions manipulate -- not the stub `date`.
set_backup_age() {
  local hours="$1"
  local stamp
  stamp=$(/bin/date -d "${hours} hours ago" +"%Y%m%d_%H%M%S")
  export STUB_LIST_KEYS="[\"backups/iqoqo_backup_${stamp}.tar.gz\"]"
}

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  export STUB_DIR="${TEST_TEMP_DIR}/stub"
  export PATH="${TEST_TEMP_DIR}/stub-bin:${PATH}"
  mkdir -p "${TEST_TEMP_DIR}/stub-bin" "${STUB_DIR}/botocore"

  # Stub df to return plenty of space
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/df"
#!/bin/bash
echo "Filesystem 1K-blocks Used Available Use% Mounted on"
echo "/dev/sda1  100000000 1000000 99000000   1% /"
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/df"

  # The check script passes the filename timestamp to `date -d`, which BSD date
  # (macOS) cannot parse. Stub `date -d` to translate the script's own format
  # into epoch seconds portably, so the age arithmetic under test is real.
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/date"
#!/bin/bash
if [[ "$*" == *"-d"* ]]; then
  for arg in "$@"; do
    case "$arg" in
      *-d*) continue ;;
    esac
    stamp="${arg//-/}"; stamp="${stamp//:/ }"; stamp="${stamp// /}"
    /bin/date -d "${stamp:0:8} ${stamp:8:2}:${stamp:10:2}:${stamp:12:2}" +%s 2>/dev/null && exit 0
  done
  exit 1
fi
/bin/date "$@"
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/date"

  # A stub rclone, so the default backend can be exercised without a network.
  cat << 'RBEOF' > "${TEST_TEMP_DIR}/stub-bin/rclone"
#!/bin/bash
if [[ "$*" == *"listremotes"* ]]; then
  echo "${RCLONE_REMOTES:-my-remote:}"
elif [[ "$*" == *"about"* ]]; then
  if [ "${RCLONE_REACHABLE:-1}" = "1" ]; then
    echo "Total: 1TB"
  else
    exit 1
  fi
elif [[ "$*" == *"lsl"* ]]; then
  if [ -n "${RCLONE_BACKUP_AGE_HOURS:-}" ]; then
    echo "  10000000 $(/bin/date -d "${RCLONE_BACKUP_AGE_HOURS} hours ago" +"%Y-%m-%d %H:%M:%S") my_backup.tar.gz"
  fi
fi
exit 0
RBEOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/rclone"

  # A stub that answers list_objects_v2 with a fixed set of keys.
  cat << 'EOF' > "${STUB_DIR}/boto3.py"
__version__ = "stub"


def client(*_args, **_kwargs):
    raise AssertionError("cloud_backup_check.sh must go through S3Service, not build its own client")
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
        self.operation_name = operation_name


class EndpointConnectionError(BotoCoreError):
    def __init__(self, endpoint_url=""):
        super().__init__(f"could not connect to {endpoint_url}")
EOF

  # STUB_LIST_KEYS is a JSON array; STUB_LIST_FAILS makes the listing raise.
  cat << 'EOF' > "${STUB_DIR}/sitecustomize.py"
import json
import os

if "STUB_BOTO_INSTALLED" not in os.environ:
    os.environ["STUB_BOTO_INSTALLED"] = "1"
    from botocore.exceptions import ClientError, EndpointConnectionError

    from app.core import s3_service

    keys = json.loads(os.environ.get("STUB_LIST_KEYS", "[]"))
    fail = os.environ.get("STUB_LIST_FAILS", "")

    class _Client:
        def get_paginator(self, _name):
            if fail == "access-denied":
                raise ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "ListObjectsV2")
            if fail == "offline":
                raise EndpointConnectionError(endpoint_url="https://s3.example")

            class _Paginator:
                def paginate(self, **_kwargs):
                    return [{"Contents": [{"Key": k} for k in keys]}]

            return _Paginator()

    s3_service.boto3.client = lambda *_a, **_k: _Client()
EOF

  export PYTHONPATH="${STUB_DIR}:${PYTHONPATH:-}"

  # An operator with rclone configured. S3 credentials are also present, to
  # prove the default selection still resolves to rclone.
  export HOME="${TEST_TEMP_DIR}/home"
  mkdir -p "${HOME}/.config/rclone"
  printf '[my-remote]\ntype = s3\n' > "${HOME}/.config/rclone/rclone.conf"

  export AWS_ACCESS_KEY_ID="AKIAEXAMPLE"
  export AWS_SECRET_ACCESS_KEY="example-secret"
  export S3_BUCKET_BACKUP="my-bucket"

  # One archive, four hours old, named with the timestamp cloud_backup.sh
  # generates. Tests needing another age call set_backup_age.
  set_backup_age 4

  # The check script resolves its Python interpreter as $(dirname $0)/../.venv and
  # cloud_backup.sh relative to its own directory, so it is placed inside a
  # project-shaped tree with the real venv symlinked in. Running under the real
  # interpreter matters: the S3 probe imports app.core.s3_service, and a bare
  # system python3 has neither boto3 nor dotenv, which would test the wrong
  # failure mode.
  export FAKE_PROJECT="${TEST_TEMP_DIR}/project"
  mkdir -p "${FAKE_PROJECT}/scripts"
  # Symlinked only when it exists. CI installs into the system interpreter
  # rather than creating a .venv, and a dangling symlink would be misleading
  # even though the check script's fallback handles it.
  if [ -d "${BATS_TEST_DIRNAME}/../../.venv" ]; then
    ln -s "$(cd "${BATS_TEST_DIRNAME}/../.." && pwd)/.venv" "${FAKE_PROJECT}/.venv"
  fi
  export CHECK_SCRIPT="${FAKE_PROJECT}/scripts/cloud_backup_check.sh"
  cp scripts/cloud_backup_check.sh "${CHECK_SCRIPT}"
  cp scripts/cloud_backup.sh "${FAKE_PROJECT}/scripts/"

  export TEMP_CRON_FILE="${TEST_TEMP_DIR}/cron-job"
  echo "* * * * * root /usr/src/app/scripts/cloud_backup.sh" > "${TEMP_CRON_FILE}"
  sed -i.bak "s|/etc/cron.d/iqoqo-backup|${TEMP_CRON_FILE}|g" "${CHECK_SCRIPT}"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

# ── Backend selection ───────────────────────────────────────────────────────

@test "cloud_backup_check.sh probes rclone by default when a remote is configured" {
  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: rclone" ]]
  # No remote named: the check confirms the config exists rather than picking a
  # destination on the operator's behalf.
  [[ "$output" =~ "[OK]  Rclone: config present" ]]
  [[ "$output" =~ "All checks passed!" ]]
}

@test "cloud_backup_check.sh prefers rclone even when S3 is also configured" {
  # Guards the regression: an existing operator with rclone must not have their
  # health check silently start reporting on a different destination.
  run bash "${CHECK_SCRIPT}" my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[OK]  Rclone remote 'my-remote': configured" ]]
  [[ ! "$output" =~ "S3 bucket" ]]
}

@test "cloud_backup_check.sh honours S3_BACKEND=s3" {
  export S3_BACKEND="s3"

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "backend: s3" ]]
  [[ "$output" =~ "[OK]  S3 bucket 'my-bucket': reachable: 1 object(s)" ]]
}

@test "cloud_backup_check.sh rejects an unknown S3_BACKEND" {
  export S3_BACKEND="gcs"

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "S3_BACKEND must be one of: auto, rclone, s3" ]]
}

@test "cloud_backup_check.sh fails when no destination is configured" {
  rm -f "${HOME}/.config/rclone/rclone.conf"
  unset S3_BUCKET_BACKUP

  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "backend: NONE CONFIGURED" ]]
  [[ "$output" =~ "[FAIL] No backup destination configured" ]]
}

# ── rclone branch ───────────────────────────────────────────────────────────

@test "cloud_backup_check.sh fails when the cron file is missing" {
  local missing="${TEST_TEMP_DIR}/nonexistent-cron"
  sed -i.bak2 "s|${TEMP_CRON_FILE}|${missing}|g" "${CHECK_SCRIPT}"

  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Cron job: not installed" ]]
}

@test "cloud_backup_check.sh fails when a named rclone remote does not exist" {
  run bash "${CHECK_SCRIPT}" non-existent-remote
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Rclone remote 'non-existent-remote': not found" ]]
}

@test "cloud_backup_check.sh fails when the rclone config is missing" {
  # Without this, auto-selection would fall through to the configured S3 bucket
  # and the rclone branch would never be reached.
  export S3_BACKEND="rclone"
  rm -f "${HOME}/.config/rclone/rclone.conf"

  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Rclone: config not found" ]]
}

@test "cloud_backup_check.sh fails when rclone is selected but not installed" {
  # This host has a real /usr/bin/rclone, so deleting the stub is not enough.
  local no_rclone_bin="${TEST_TEMP_DIR}/no-rclone-bin"
  mkdir -p "${no_rclone_bin}"
  for tool in bash sh date awk sort tail grep sed head basename dirname env cat; do
    target=$(command -v "${tool}" || true)
    [ -n "${target}" ] && ln -sf "${target}" "${no_rclone_bin}/${tool}"
  done
  # The script reaches its disk check before exiting, so `df` must resolve.
  ln -sf "$(command -v df)" "${no_rclone_bin}/df"

  run env PATH="${no_rclone_bin}" S3_BACKEND=rclone bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Rclone: not installed" ]]
}

@test "cloud_backup_check.sh warns when a configured remote is unreachable" {
  export RCLONE_REACHABLE=0

  run bash "${CHECK_SCRIPT}" my-remote
  # The cron job is installed, so a reachability problem is a warning to
  # investigate rather than a hard failure of the check itself.
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] Rclone remote 'my-remote': configured but unreachable" ]]
}

@test "cloud_backup_check.sh reports a fresh rclone backup as OK" {
  export RCLONE_BACKUP_AGE_HOURS=4

  run bash "${CHECK_SCRIPT}" my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[OK]  Last backup: 4h ago" ]]
}

@test "cloud_backup_check.sh fails when the newest rclone backup is stale" {
  export RCLONE_BACKUP_AGE_HOURS=72

  run bash "${CHECK_SCRIPT}" my-remote
  [ "$status" -ne 0 ]
  [[ "$output" =~ "STALE" ]]
}

@test "cloud_backup_check.sh warns when the newest rclone backup is over 24h old" {
  export RCLONE_BACKUP_AGE_HOURS=30

  run bash "${CHECK_SCRIPT}" my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] Last backup: 30h ago (over 24h)" ]]
}

# ── S3 branch ───────────────────────────────────────────────────────────────

@test "cloud_backup_check.sh fails when S3 is selected but S3_BUCKET_BACKUP is unset" {
  export S3_BACKEND="s3"
  unset S3_BUCKET_BACKUP

  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] S3: S3_BUCKET_BACKUP is not set" ]]
}

@test "cloud_backup_check.sh fails when a bucket is set but credentials are not" {
  export S3_BACKEND="s3"
  unset AWS_SECRET_ACCESS_KEY

  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] S3: my-bucket set but AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY missing" ]]
}

@test "cloud_backup_check.sh warns rather than fails when the bucket rejects the request" {
  export S3_BACKEND="s3"
  export STUB_LIST_FAILS="access-denied"

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] S3 bucket 'my-bucket'" ]]
  # The message names the failure class without leaking botocore's text.
  [[ "$output" =~ "unreachable" ]]
}

@test "cloud_backup_check.sh warns when the S3 endpoint is unreachable" {
  export S3_BACKEND="s3"
  export STUB_LIST_FAILS="offline"

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] S3 bucket 'my-bucket'" ]]
}

@test "cloud_backup_check.sh reports a fresh S3 backup as OK" {
  export S3_BACKEND="s3"
  # 4 hours old, so the real age arithmetic must surface "4h ago" rather than
  # falling through to the unparseable-timestamp warning.
  set_backup_age 4

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[OK]  Last backup: 4h ago" ]]
}

@test "cloud_backup_check.sh fails when the newest S3 backup is stale" {
  export S3_BACKEND="s3"
  set_backup_age 72

  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "STALE" ]]
}

@test "cloud_backup_check.sh warns when the newest S3 backup is over 24h old" {
  export S3_BACKEND="s3"
  set_backup_age 30

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] Last backup: 30h ago (over 24h)" ]]
}

@test "cloud_backup_check.sh warns when no archive exists in the S3 bucket" {
  export S3_BACKEND="s3"
  export STUB_LIST_KEYS='[]'

  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] Last backup: none found" ]]
}

@test "cloud_backup_check.sh --archive checks iqoqo-archive cron file" {
  export TEMP_ARCHIVE_CRON="${TEST_TEMP_DIR}/archive-cron-job"
  echo "0 4 1 * * root /usr/src/app/scripts/cloud_backup.sh" > "${TEMP_ARCHIVE_CRON}"
  sed -i.bak "s|/etc/cron.d/iqoqo-archive|${TEMP_ARCHIVE_CRON}|g" "${CHECK_SCRIPT}"

  run bash "${CHECK_SCRIPT}" --archive my-remote
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Checking iQoQo archive configuration" ]]
  [[ "$output" =~ "Cron job: ${TEMP_ARCHIVE_CRON} exists" ]]
}

# ── Duplicate cron, lock status, and configuration validation ───────────────

@test "cloud_backup_check.sh warns on duplicate cron entries" {
  echo "* * * * * root /usr/src/app/scripts/cloud_backup.sh" >> "${TEMP_CRON_FILE}"
  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] Cron job: duplicate entries detected" ]]
}

@test "cloud_backup_check.sh reports lock file free status when lock is unheld" {
  local lock_file="${TEST_TEMP_DIR}/check_test.lock"
  export BACKUP_LOCK_FILE="${lock_file}"
  touch "${lock_file}"
  chmod 0600 "${lock_file}"
  run bash "${CHECK_SCRIPT}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Lock file: ${lock_file}" ]]
  [[ "$output" =~ "status: free" ]]
}

@test "cloud_backup_check.sh warns when lock file is held by active backup" {
  local lock_file="${TEST_TEMP_DIR}/check_test.lock"
  export BACKUP_LOCK_FILE="${lock_file}"
  exec 8>"${lock_file}"
  flock 8

  run bash "${CHECK_SCRIPT}"
  exec 8>&-
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] Lock file: ${lock_file}" ]]
  [[ "$output" =~ "status: held by active backup" ]]
}

@test "cloud_backup_check.sh fails when BACKUP_LOCK_TIMEOUT is invalid" {
  export BACKUP_LOCK_TIMEOUT="invalid"
  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Config: BACKUP_LOCK_TIMEOUT must be a positive integer" ]]
}

@test "cloud_backup_check.sh fails when BACKUP_RETRY_ATTEMPTS is invalid" {
  export BACKUP_RETRY_ATTEMPTS="0"
  run bash "${CHECK_SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "[FAIL] Config: BACKUP_RETRY_ATTEMPTS must be a positive integer" ]]
}

