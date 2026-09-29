#!/bin/bash
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
# Mock-based test for cloud_backup.sh.
#
# Both upload backends are exercised without any network access: a stub `rclone`
# binary and a stub boto3 module on PYTHONPATH each record what they were asked
# to do. This verifies backend selection, the pg_dumpall guard, and the
# cleanup-on-success / preserve-on-failure behaviour.

set -e

echo "Testing cloud_backup.sh logic..."

TEST_DIR=$(mktemp -d)
BIN_DIR="${TEST_DIR}/bin"
STUB_DIR="${TEST_DIR}/stub"
mkdir -p "${BIN_DIR}" "${STUB_DIR}"
trap 'rm -rf "${TEST_DIR}"' EXIT

failures=0
pass() { echo "  [PASS] $1"; }
fail() {
    echo "  [FAIL] $1" >&2
    failures=$((failures + 1))
}

# --- Mock docker (cloud_backup.sh invokes `docker compose ... exec -T db pg_dumpall ...`) ---
cat > "${BIN_DIR}/docker" <<'EOF'
#!/bin/bash
if [ "$1" == "compose" ] || [ "$1" == "exec" ]; then
    echo "CREATE TABLE manifestations (id integer);"
    echo "INSERT INTO manifestations VALUES (1);"
fi
EOF
chmod +x "${BIN_DIR}/docker"

# Stub rclone: records how it was called, and can be made to fail.
cat <<'EOF' > "${BIN_DIR}/rclone"
#!/bin/bash
echo "RCLONE_CALLED_WITH: $*" >> "${RCLONE_LOG}"
if [ "${RCLONE_SHOULD_FAIL:-0}" = "1" ]; then
  exit 1
fi
exit 0
EOF
chmod +x "${BIN_DIR}/rclone"

export PATH="${BIN_DIR}:${PATH}"

# --- Stub boto3 ---
# Records the call so the harness can assert on bucket, key and encryption
# without a network round-trip.
cat > "${STUB_DIR}/boto3.py" <<'EOF'
__version__ = "stub"

def client(*_args, **kwargs):
    raise AssertionError("cloud_backup.sh must not build its own client; it uses S3Service")
EOF
mkdir -p "${STUB_DIR}/botocore"
cat > "${STUB_DIR}/botocore/__init__.py" <<'EOF'
EOF
cat > "${STUB_DIR}/botocore/config.py" <<'EOF'
class Config:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
EOF
cat > "${STUB_DIR}/botocore/exceptions.py" <<'EOF'
class BotoCoreError(Exception):
    pass


class ClientError(Exception):
    pass


class EndpointConnectionError(BotoCoreError):
    pass
EOF
export PYTHONPATH="${STUB_DIR}:${PYTHONPATH:-}"

# cloud_backup.sh imports app.core.s3_service, which imports boto3 and
# botocore. The stub above satisfies both; the recording happens in the
# stubbed S3Service's client below.
cat > "${STUB_DIR}/record_upload.py" <<'EOF'
import json
import os
import sys

record_path = os.environ["UPLOAD_RECORD"]


class _Client:
    def upload_file(self, local_path, bucket, key, ExtraArgs=None):  # noqa: N803
        if not os.path.isfile(local_path):
            raise AssertionError(f"upload_file was given a missing path: {local_path}")
        with open(record_path, "w", encoding="utf-8") as handle:
            json.dump({"local_path": local_path, "bucket": bucket, "key": key, "extra": ExtraArgs}, handle)


def install():
    """Replace S3Service's boto3 client with the recording stub."""
    from app.core import s3_service

    s3_service.boto3.client = lambda *_a, **_k: _Client()
EOF

# An operator-shaped environment: rclone is configured, so it is the default
# backend. S3 credentials are also set, to prove rclone still wins.
export HOME="${TEST_DIR}/home"
mkdir -p "${HOME}/.config/rclone"
printf '[iqoqo-backup]\ntype = s3\n' > "${HOME}/.config/rclone/rclone.conf"
export RCLONE_REMOTE_FAST="iqoqo-backup"
export RCLONE_LOG="${TEST_DIR}/rclone.log"
: > "${RCLONE_LOG}"

export COMPOSE_PROJECT_NAME="iqoqo-test"
export POSTGRES_USER="testuser"
export AWS_ACCESS_KEY_ID="AKIAEXAMPLE"
export AWS_SECRET_ACCESS_KEY="example-secret"
export S3_BUCKET_BACKUP="iqoqo-backup-test"
export S3_SSE="AES256"
export UPLOAD_RECORD="${TEST_DIR}/upload.json"

# The script runs `${PYTHON_BIN} -` with a heredoc, so the recording install
# has to happen inside that interpreter. Preload it via sitecustomize, which
# Python imports automatically at startup.
cat > "${STUB_DIR}/sitecustomize.py" <<'EOF'
import os

if "UPLOAD_RECORD" in os.environ:
    import record_upload

    record_upload.install()
EOF

# --- 1. Happy path, rclone backend (the default) ---
if bash ./scripts/cloud_backup.sh > "${TEST_DIR}/run.log" 2>&1; then
    if grep -qE "RCLONE_CALLED_WITH: copy .* iqoqo-backup:iqoqo_backups$" "${RCLONE_LOG}"; then
        pass "backup completed via rclone to the configured remote"
    else
        fail "script exited 0 but rclone was not called with the expected target"
    fi
    if [ -f "${UPLOAD_RECORD}" ]; then
        fail "an S3 upload was attempted even though rclone was available"
    fi
else
    fail "script exited non-zero: $(tail -5 "${TEST_DIR}/run.log")"
fi

# --- 2. S3 backend, when explicitly selected ---
rm -f "${UPLOAD_RECORD}"
: > "${RCLONE_LOG}"
if S3_BACKEND=s3 bash ./scripts/cloud_backup.sh > "${TEST_DIR}/s3run.log" 2>&1; then
    pass "backup completed via the S3 backend"
else
    fail "S3 backend exited non-zero: $(tail -5 "${TEST_DIR}/s3run.log")"
fi

if [ -f "${UPLOAD_RECORD}" ]; then
    BUCKET=$(.venv/bin/python -c "import json;print(json.load(open('${UPLOAD_RECORD}'))['bucket'])")
    KEY=$(.venv/bin/python -c "import json;print(json.load(open('${UPLOAD_RECORD}'))['key'])")
    EXTRA=$(.venv/bin/python -c "import json;print(json.load(open('${UPLOAD_RECORD}'))['extra'])")

    if [ "${BUCKET}" = "iqoqo-backup-test" ]; then
        pass "upload used S3_BUCKET_BACKUP (${BUCKET})"
    else
        fail "upload used bucket '${BUCKET}', expected iqoqo-backup-test"
    fi

    case "${KEY}" in
        backups/iqoqo_backup_*.tar.gz) pass "key layout is backups/iqoqo_backup_<ts>.tar.gz (${KEY})" ;;
        *) fail "unexpected key layout: ${KEY}" ;;
    esac

    case "${EXTRA}" in
        *AES256*) pass "server-side encryption applied (${EXTRA})" ;;
        *) fail "server-side encryption not applied: ${EXTRA}" ;;
    esac
fi

# --- 3. Cleanup on success ---
if ls /tmp/iqoqo_backup_*.tar.gz >/dev/null 2>&1; then
    fail "local archive was not cleaned up after a successful upload"
else
    pass "local archive cleaned up after a successful upload"
fi

if [ -s "${RCLONE_LOG}" ]; then
    fail "rclone was called even though S3_BACKEND=s3"
else
    pass "rclone was not called when S3_BACKEND=s3"
fi

# --- 4. Missing S3_BUCKET_BACKUP aborts before doing the work ---
rm -f "${UPLOAD_RECORD}"
if env -u S3_BUCKET_BACKUP S3_BACKEND=s3 bash ./scripts/cloud_backup.sh > "${TEST_DIR}/nobucket.log" 2>&1; then
    fail "script succeeded without S3_BUCKET_BACKUP"
else
    if grep -q "S3_BUCKET_BACKUP" "${TEST_DIR}/nobucket.log"; then
        pass "missing S3_BUCKET_BACKUP aborts with a named error"
    else
        fail "aborted, but the error did not name S3_BUCKET_BACKUP"
    fi
    if [ ! -f "${UPLOAD_RECORD}" ]; then
        pass "no upload was attempted when unconfigured"
    else
        fail "an upload was attempted despite the missing bucket"
    fi
fi

# --- 5. Missing credentials abort ---
if env -u AWS_SECRET_ACCESS_KEY S3_BACKEND=s3 bash ./scripts/cloud_backup.sh > "${TEST_DIR}/nocreds.log" 2>&1; then
    fail "script succeeded without AWS_SECRET_ACCESS_KEY"
else
    pass "missing credentials abort the run"
fi

# --- 6. A failed rclone upload preserves the local archive ---
if RCLONE_SHOULD_FAIL=1 bash ./scripts/cloud_backup.sh > "${TEST_DIR}/failrclone.log" 2>&1; then
    fail "script reported success despite a failed rclone upload"
else
    preserved=$(ls /tmp/iqoqo_backup_*.tar.gz 2>/dev/null | head -1)
    if [ -n "${preserved}" ]; then
        pass "failed rclone upload preserves the local archive (${preserved})"
        rm -f "${preserved}"
    else
        fail "failed rclone upload destroyed the only copy of the backup"
    fi
    if grep -q "Archive preserved" "${TEST_DIR}/failrclone.log"; then
        pass "rclone failure message points at the preserved archive"
    else
        fail "rclone failure message did not mention the preserved archive"
    fi
fi

# --- 7. A failed S3 upload preserves the local archive ---
cat > "${STUB_DIR}/record_upload.py" <<'EOF'
import os

record_path = os.environ["UPLOAD_RECORD"]


class _Client:
    def upload_file(self, *_args, **_kwargs):
        with open(record_path, "w", encoding="utf-8") as handle:
            handle.write("failed")
        raise RuntimeError("simulated transport failure")


def install():
    from app.core import s3_service

    s3_service.boto3.client = lambda *_a, **_k: _Client()
EOF

rm -f "${UPLOAD_RECORD}"
if S3_BACKEND=s3 bash ./scripts/cloud_backup.sh > "${TEST_DIR}/failupload.log" 2>&1; then
    fail "script reported success despite a failed upload"
else
    preserved=$(ls /tmp/iqoqo_backup_*.tar.gz 2>/dev/null | head -1)
    if [ -n "${preserved}" ]; then
        pass "failed upload preserves the local archive (${preserved})"
        rm -f "${preserved}"
    else
        fail "failed upload destroyed the only copy of the backup"
    fi
    if grep -q "Archive preserved" "${TEST_DIR}/failupload.log"; then
        pass "failure message points at the preserved archive"
    else
        fail "failure message did not mention the preserved archive"
    fi
fi

# --- 8. An empty pg_dumpall aborts before any upload ---
cat > "${BIN_DIR}/docker" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "${BIN_DIR}/docker"
rm -f "${UPLOAD_RECORD}"
if bash ./scripts/cloud_backup.sh > "${TEST_DIR}/emptydump.log" 2>&1; then
    fail "script succeeded with an empty database dump"
else
    if [ ! -f "${UPLOAD_RECORD}" ]; then
        pass "empty dump aborts before the upload is attempted"
    else
        fail "an empty dump was uploaded as if it were a backup"
    fi
    if grep -q "empty" "${TEST_DIR}/emptydump.log"; then
        pass "empty-dump error names the cause"
    else
        fail "empty-dump error did not name the cause"
    fi
fi

echo ""
if [ "$failures" -eq 0 ]; then
    echo "All cloud_backup.sh tests passed."
    exit 0
fi
echo "${failures} test(s) failed."
exit 1
