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
# iQoQo Cloud Backup Script
# Usage: ./scripts/cloud_backup.sh [rclone_remote]
#
# Backs up:
#   1. PostgreSQL full database dump (pg_dumpall)
#   2. Uploaded asset volumes (covers/, data/)
# Then compresses and syncs to off-site storage.
#
# ── Two upload backends ────────────────────────────────────────────────────
#
# This is a HOST-side script; it runs on the operator's machine, not in a
# container. That is what makes rclone appropriate here: it reaches any of
# ~40 backends (Backblaze B2, Google Drive, Dropbox, SFTP, Wasabi, ...), and the
# operator's existing rclone.conf keeps working unchanged.
#
#   1. rclone (default). Requires `rclone` on the host and a configured remote.
#      Selected when a remote name is given as $1, or RCLONE_REMOTE_FAST is set,
#      or ~/.config/rclone/rclone.conf exists. This is the pre-existing path and
#      stays the default.
#
#   2. S3-compatible (fallback / opt-in). Used only when S3_BACKEND=s3, or when
#      no rclone remote and no rclone.conf are present. Reads the standard
#      variables the application itself uses (AWS_ACCESS_KEY_ID,
#      AWS_SECRET_ACCESS_KEY, S3_BUCKET_BACKUP, optional S3_ENDPOINT_URL), so
#      boto3 is the same code path in-container and here.
#
# This script is the ONLY backup path. There is deliberately no in-container
# rotation: `BackupManager` and `rotate_and_archive_backups` were removed
# because they were unreachable (no beat-schedule entry, and `/data/backups` was
# never mounted), so off-site archiving runs here and only here.
#
# The asymmetry with the container is deliberate, not an oversight. In-container
# code reads S3 credentials from the environment via app/core/s3_service.py,
# because a plaintext rclone.conf bind-mounted next to a process that parses
# untrusted input was a real exposure. On the host there is no such exposure:
# the operator created the config and administers it.

set -euo pipefail

# MOD-OPS-11: backups contain a full pg_dumpall of the instance database, which
# includes user rows, password hashes and API tokens. Restrict every file this
# script creates (dump, per-asset tarballs, final archive) to owner-only
# access before anything touches the filesystem. umask applies to files created
# later via open()/creat(), and is not affected by a later chmod on the parent
# directory, so it must be set here at initialisation.
umask 077

if [ -f "$(dirname "$0")/../.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$(dirname "$0")/../.env"
    set +a
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/iqoqo_backup_${TIMESTAMP}"
ARCHIVE="${BACKUP_DIR}.tar.gz"

# ── Backend selection ───────────────────────────────────────────────────────
#
# rclone stays the default because it is what an existing deployment already
# uses, and because it reaches backends boto3 cannot. The S3 path is selected
# only when explicitly asked for, or when there is no rclone setup at all — in
# which case trying rclone would just fail with a confusing "unknown remote".
RCLONE_REMOTE="${1:-${RCLONE_REMOTE_FAST:-}}"
RCLONE_CONF="${RCLONE_CONFIG:-${HOME}/.config/rclone/rclone.conf}"

# Auto-selection keys off the config *file*, not off RCLONE_REMOTE_FAST.
# .env.example ships RCLONE_REMOTE_FAST=iqoqo-backup, so keying off the
# variable would make a copied .env hijack an S3-only deployment the moment
# rclone happened to be installed for some unrelated reason. A config file is
# unambiguous evidence of an rclone setup.
rclone_conf_present() { [ -f "${RCLONE_CONF}" ]; }

BACKEND=""
# Coerced, not just defaulted: `${VAR:-auto}` substitutes only when the
# variable is unset, and a .env declaring `S3_BACKEND=` sets it to the
# empty string, which would otherwise hit the reject branch below.
S3_BACKEND="${S3_BACKEND:-auto}"
case "${S3_BACKEND}" in
    rclone) BACKEND="rclone" ;;
    s3)     BACKEND="s3" ;;
    auto)
        if rclone_conf_present; then
            BACKEND="rclone"
        elif [ -n "${S3_BUCKET_BACKUP:-}" ]; then
            BACKEND="s3"
        else
            BACKEND="none"
        fi
        ;;
    *)
        echo "❌ Error: S3_BACKEND must be one of: auto, rclone, s3 (got '${S3_BACKEND}')" >&2
        exit 1
        ;;
esac

# An explicit remote argument is an unambiguous request for rclone, so honour
# it over S3_BACKEND=auto rather than silently using a different backend.
if [ -n "${1:-}" ] && [ "${S3_BACKEND}" = "auto" ]; then
    BACKEND="rclone"
fi

# Validate the selected backend BEFORE the pg_dumpall, so a misconfigured host
# does not spend several minutes producing an archive with nowhere to go.
case "${BACKEND}" in
    rclone)
        if ! command -v rclone >/dev/null 2>&1; then
            echo "❌ Error: rclone is not installed but is the selected backend." >&2
            echo "   Install it, or set S3_BACKEND=s3 to use S3-compatible storage." >&2
            exit 1
        fi
        if [ ! -f "${RCLONE_CONF}" ]; then
            echo "❌ Error: rclone config not found at ${RCLONE_CONF}." >&2
            echo "   Create it with: rclone config   (then verify: rclone listremotes)" >&2
            exit 1
        fi
        # A bare remote name gets the historical iqoqo_backups subdirectory;
        # an explicit remote:path is used verbatim.
        if [[ "${RCLONE_REMOTE}" == *":"* ]]; then
            RCLONE_TARGET="${RCLONE_REMOTE}"
        else
            RCLONE_TARGET="${RCLONE_REMOTE:-iqoqo-backup}:iqoqo_backups"
        fi
        ;;
    s3)
        if [ -z "${S3_BUCKET_BACKUP:-}" ]; then
            echo "❌ Error: S3_BUCKET_BACKUP is not set but S3_BACKEND=s3." >&2
            echo "   Set S3_BUCKET_BACKUP plus AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY." >&2
            exit 1
        fi
        if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
            echo "❌ Error: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must both be set." >&2
            exit 1
        fi
        # Resolve an interpreter that has boto3. The project venv is preferred;
        # system python3 is the fallback for hosts that install boto3 globally.
        if [ -x "$(dirname "$0")/../.venv/bin/python" ]; then
            PYTHON_BIN="$(dirname "$0")/../.venv/bin/python"
        elif command -v python3 >/dev/null 2>&1; then
            PYTHON_BIN="python3"
        else
            echo "❌ Error: no python3 interpreter found. Install Python 3 or create the venv." >&2
            exit 1
        fi
        if ! "${PYTHON_BIN}" -c "import boto3" >/dev/null 2>&1; then
            echo "❌ Error: boto3 is not available to ${PYTHON_BIN}." >&2
            echo "   Install it with: ${PYTHON_BIN} -m pip install boto3" >&2
            echo "   (or run from the project venv: make venv)" >&2
            exit 1
        fi
        S3_KEY_PREFIX="${S3_KEY_PREFIX:-backups/}"
        # Normalise to exactly one separator, so the key is
        # "${S3_KEY_PREFIX}iqoqo_backup_<ts>.tar.gz" however the operator wrote it.
        S3_KEY_PREFIX="${S3_KEY_PREFIX#/}"
        S3_KEY_PREFIX="${S3_KEY_PREFIX%/}"
        [ -n "${S3_KEY_PREFIX}" ] && S3_KEY_PREFIX="${S3_KEY_PREFIX}/"
        ;;
    none)
        echo "❌ Error: no backup destination is configured." >&2
        echo "   Either configure rclone (rclone config), or set in .env:" >&2
        echo "     S3_BUCKET_BACKUP=<bucket>" >&2
        echo "     AWS_ACCESS_KEY_ID=<key>" >&2
        echo "     AWS_SECRET_ACCESS_KEY=<secret>" >&2
        exit 1
        ;;
esac

case "${BACKEND}" in
    rclone) echo "🗄️  Starting iQoQo backup (backend: rclone, target: ${RCLONE_TARGET})..." ;;
    s3)     echo "🗄️  Starting iQoQo backup (backend: s3, bucket: ${S3_BUCKET_BACKUP}, prefix: ${S3_KEY_PREFIX:-<root>})..." ;;
esac
mkdir -p "${BACKUP_DIR}"

# 1. Dump PostgreSQL
DB_DUMP_FILE="${BACKUP_DIR}/db_dump_${TIMESTAMP}.sql"
# Use specific filter to match only iqoqo PostgreSQL container, not other DB containers
DB_CONTAINER=$(docker ps --filter "name=iqoqo-db" --filter "status=running" --format "{{.Names}}" | head -1)
if [ -n "${DB_CONTAINER}" ]; then
    echo "📊 Using database container: ${DB_CONTAINER}"
    # Explicitly set PGHOST to ensure connection inside container, not to host PostgreSQL
    docker exec -i "${DB_CONTAINER}" sh -c "PGHOST=/var/run/postgresql pg_dumpall -c -U '${POSTGRES_USER:-iqoqo}'" > "${DB_DUMP_FILE}"
else
    echo "⚠️  No running iqoqo-db container found, falling back to docker compose"
    COMPOSE_SPEC="${COMPOSE_FILE:-docker-compose.yml}"
    docker compose -f "${COMPOSE_SPEC}" exec -T db \
        sh -c "PGHOST=/var/run/postgresql pg_dumpall -c -U '${POSTGRES_USER:-iqoqo}'" \
        > "${DB_DUMP_FILE}"
fi

# Guard against a silent partial/empty dump (e.g. auth failure inside the
# container, or the db service restarting mid-dump) slipping through as a
# "successful" backup -- pg_dumpall exiting 0 doesn't guarantee non-empty
# output in every failure mode.
if [ ! -s "${DB_DUMP_FILE}" ]; then
    echo "❌ Error: PostgreSQL dump is empty (${DB_DUMP_FILE}). Aborting backup." >&2
    rm -rf "${BACKUP_DIR}"
    exit 1
fi

# Additional validation: check that the dump contains actual SQL content
# (not just error messages or empty transaction wrappers)
if ! grep -q "CREATE\|INSERT\|ALTER\|SET" "${DB_DUMP_FILE}" 2>/dev/null; then
    echo "❌ Error: PostgreSQL dump appears invalid (no SQL statements found). Aborting backup." >&2
    echo "First 10 lines of dump file:" >&2
    head -10 "${DB_DUMP_FILE}" >&2
    rm -rf "${BACKUP_DIR}"
    exit 1
fi

# 2. Archive uploaded assets (non-fatal if missing)
# Standard iQoQo asset paths relative to app root/volumes
ASSET_PATHS=("app/static/covers" "app/static/gallery" "app/static/uploads/raw_covers")
for asset_dir in "${ASSET_PATHS[@]}"; do
    if [ -d "${asset_dir}" ]; then
        echo "📁 Archiving ${asset_dir}..."
        tar -czf "${BACKUP_DIR}/$(basename "${asset_dir}")_${TIMESTAMP}.tar.gz" "${asset_dir}"
    fi
done

# 3. Compress everything
echo "🗜️  Compressing archive..."
tar -czf "${ARCHIVE}" -C /tmp "iqoqo_backup_${TIMESTAMP}"

# 4. Upload off-site.
#
# Two branches, one contract: on success the local archive may be removed, on
# failure it must survive. That is the whole safety property of this step.
upload_ok=false

case "${BACKEND}" in
    rclone)
        # `--` is the POSIX end-of-options delimiter: a timestamped filename
        # starting with a dash would otherwise be parsed as a flag.
        echo "☁️  Syncing via rclone to ${RCLONE_TARGET}..."
        # HOME may be unset under cron; without this rclone looks for its
        # config in a relative path and writes one somewhere unexpected.
        export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME:-/root}/.config}"
        if rclone copy --s3-no-check-bucket -- "${ARCHIVE}" "${RCLONE_TARGET}"; then
            echo "✅ Backup synced → ${RCLONE_TARGET}"
            upload_ok=true
        fi
        ;;

    s3)
        # The upload runs through a small inline Python program rather than a
        # second credential file. It reads the same environment variables as the
        # application, so one S3 configuration covers both, and applies the same
        # server-side-encryption setting the in-container cache uses.
        #
        # upload_file is used rather than put_object so the archive streams in
        # bounded chunks instead of being read into memory whole -- a pg_dumpall
        # archive of a real library is routinely multiple gigabytes.
        echo "☁️  Uploading to ${S3_BUCKET_BACKUP}/${S3_KEY_PREFIX}..."
        if ARCHIVE_PATH="${ARCHIVE}" BUCKET="${S3_BUCKET_BACKUP}" KEY_PREFIX="${S3_KEY_PREFIX}" "${PYTHON_BIN}" - <<'PYEOF'
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

try:
    from app.core.s3_service import S3Service, S3UploadError
except ImportError:
    sys.exit("error: could not import app.core.s3_service — run from the project root, or use the project venv")

archive = os.environ["ARCHIVE_PATH"]
bucket = os.environ["BUCKET"]
prefix = os.environ.get("KEY_PREFIX", "")

service = S3Service("backup", access_key=os.environ.get("AWS_ACCESS_KEY_ID"), secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))
# The bucket is assigned rather than read from the environment so the same
# process-local resolution rules as the application apply.
service._bucket = bucket  # pylint: disable=protected-access

key = f"{prefix}{os.path.basename(archive)}"
extra = service._extra_args()  # pylint: disable=protected-access

try:
    service.upload_file(archive, key, content_type="application/gzip")
except S3UploadError as exc:
    sys.exit(f"error: {exc}")

if extra.get("ServerSideEncryption"):
    print(f"  encrypted at rest with {extra['ServerSideEncryption']}")
print(f"  wrote {key}")
PYEOF
        then
            echo "✅ Backup uploaded → ${S3_BUCKET_BACKUP}/${S3_KEY_PREFIX}$(basename "${ARCHIVE}")"
            upload_ok=true
        fi
        ;;
esac

if [ "${upload_ok}" != true ]; then
    echo "❌ Cloud upload failed! Archive preserved at: ${ARCHIVE}" >&2
    exit 1
fi

# 5. Cleanup only on successful sync
echo "🧹 Cleaning up local temp files..."
rm -rf "${BACKUP_DIR}" "${ARCHIVE}"

echo "✅ Backup completed successfully"
