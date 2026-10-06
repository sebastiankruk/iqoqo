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
# iQoQo Backup Health Check
# Usage: ./scripts/cloud_backup_check.sh [rclone_remote]
#
# Checks:
#   1. Cron job installed
#   2. Backup destination reachable (rclone remote, or S3 bucket)
#   3. Last backup freshness (pass <24h, warn 24-48h, fail >48h)
#   4. Available disk space
#   5. Backup script syntax
#
# The destination is resolved exactly as cloud_backup.sh resolves it, so this
# check cannot pass while the nightly job is failing.

set -euo pipefail

errors=0

# Resolve a Python interpreter that may have boto3, for the S3 branch only.
if [ -x "$(dirname "$0")/../.venv/bin/python" ]; then
  PYTHON_BIN="$(dirname "$0")/../.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

# Resolve the destination the same way cloud_backup.sh does. Disagreeing here
# would produce a green health check for a backup that is not actually running.
IS_ARCHIVE=false
if [ "${1:-}" = "--archive" ]; then
  IS_ARCHIVE=true
  shift
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
if [ -f "${ENV_FILE}" ]; then
  set -a
  # The path is a variable resolved at runtime, so shellcheck cannot follow it.
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if [ "${IS_ARCHIVE}" = true ]; then
  JOB_TYPE="archive"
  CRON_FILE="/etc/cron.d/iqoqo-archive"
  REMOTE="${1:-${RCLONE_REMOTE_ARCHIVE:-}}"
else
  JOB_TYPE="backup"
  CRON_FILE="/etc/cron.d/iqoqo-backup"
  REMOTE="${1:-${RCLONE_REMOTE_FAST:-}}"
fi

RCLONE_CONF="${RCLONE_CONFIG:-${HOME:-/root}/.config/rclone/rclone.conf}"

# If running as root (e.g. from cron) and no rclone config is found in /root,
# check if the owner of the project directory has an rclone configuration.
if [ ! -f "${RCLONE_CONF}" ] && [ "$(id -u)" -eq 0 ]; then
  proj_owner=$(stat -c '%U' "$(dirname "$0")/.." 2>/dev/null || true)
  if [ -n "${proj_owner}" ] && [ "${proj_owner}" != "root" ]; then
    owner_conf=$(eval echo "~${proj_owner}/.config/rclone/rclone.conf")
    if [ -f "${owner_conf}" ]; then
      RCLONE_CONF="${owner_conf}"
      export RCLONE_CONFIG="${owner_conf}"
    fi
  fi
fi

BACKEND=""
# Coerced, not just defaulted: `${VAR:-auto}` substitutes only when the
# variable is unset, and a .env declaring `S3_BACKEND=` sets it to the
# empty string, which would otherwise hit the reject branch below.
S3_BACKEND="${S3_BACKEND:-auto}"
case "${S3_BACKEND}" in
  rclone) BACKEND="rclone" ;;
  s3)     BACKEND="s3" ;;
  auto)
    # Keyed off the config file, not RCLONE_REMOTE_FAST -- see the note in
    # cloud_backup.sh: .env.example ships a default remote name, and that must
    # not hijack an S3-only deployment.
    if [ -f "${RCLONE_CONF}" ]; then
      BACKEND="rclone"
    elif [ -n "${S3_BUCKET_BACKUP:-}" ]; then
      BACKEND="s3"
    else
      BACKEND="none"
    fi
    ;;
  *)
    echo "ERROR: S3_BACKEND must be one of: auto, rclone, s3 (got '${S3_BACKEND}')" >&2
    exit 1
    ;;
esac
[ -n "${1:-}" ] && [ "${S3_BACKEND}" = "auto" ] && BACKEND="rclone"

check() {
  local status="$1" msg="$2"
  case "${status}" in
    ok)  echo "  [OK]  ${msg}" ;;
    warn) echo "  [WARN] ${msg}" ;;
    fail) echo "  [FAIL] ${msg}"; errors=$((errors + 1)) ;;
  esac
}

case "${BACKEND}" in
  rclone) echo "Checking iQoQo ${JOB_TYPE} configuration (backend: rclone, remote: ${REMOTE:-default})..." ;;
  s3)     echo "Checking iQoQo ${JOB_TYPE} configuration (backend: s3, bucket: ${S3_BUCKET_BACKUP:-<unset>})..." ;;
  none)   echo "Checking iQoQo ${JOB_TYPE} configuration (backend: NONE CONFIGURED)..." ;;
esac
echo ""

# 1. Cron job
if [ -f "${CRON_FILE}" ]; then
  check ok "Cron job: ${CRON_FILE} exists"
  if grep -q "cloud_backup.sh" "${CRON_FILE}" 2>/dev/null; then
    check ok "Cron job: references cloud_backup.sh"
  else
    check fail "Cron job: unexpected content"
  fi
else
  check fail "Cron job: not installed"
fi

# 2. Destination reachability
#
# Probed on the backend cloud_backup.sh will actually use. A destination that
# is configured but unreachable is a warning rather than a failure: the cron
# job is installed, and the operator needs to know which of the two problems
# this is (permissions vs network) rather than just "check failed".
if [ "${BACKEND}" = "rclone" ]; then
  if ! command -v rclone >/dev/null 2>&1; then
    check fail "Rclone: not installed but is the selected backend"
  elif [ ! -f "${RCLONE_CONF}" ]; then
    check fail "Rclone: config not found at ${RCLONE_CONF}"
  else
    RCLONE_REMOTE_NAME="${REMOTE%%:*}"
    if [ -z "${RCLONE_REMOTE_NAME}" ]; then
      # No named remote: the config exists, which is the most that can be
      # asserted without picking a destination on the operator's behalf.
      check ok "Rclone: config present at ${RCLONE_CONF}"
    elif rclone listremotes 2>/dev/null | grep -q "^${RCLONE_REMOTE_NAME}:"; then
      check ok "Rclone remote '${RCLONE_REMOTE_NAME}': configured"
      if rclone about "${RCLONE_REMOTE_NAME}:" >/dev/null 2>&1; then
        check ok "Rclone remote '${RCLONE_REMOTE_NAME}': reachable"
      else
        check warn "Rclone remote '${RCLONE_REMOTE_NAME}': configured but unreachable"
      fi
    else
      check fail "Rclone remote '${RCLONE_REMOTE_NAME}': not found"
    fi
  fi
elif [ "${BACKEND}" = "s3" ]; then
  if [ -z "${S3_BUCKET_BACKUP:-}" ]; then
    check fail "S3: S3_BUCKET_BACKUP is not set"
  elif [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    check fail "S3: ${S3_BUCKET_BACKUP} set but AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY missing"
  elif ! "${PYTHON_BIN}" -c "import boto3" >/dev/null 2>&1; then
    check fail "S3: boto3 not importable by ${PYTHON_BIN}"
  elif S3_PROBE=$(
    BUCKET="${S3_BUCKET_BACKUP}" "${PYTHON_BIN}" - <<'PROBE' 2>&1
import os
import sys

from app.core.s3_service import S3Service

service = S3Service(
    "backup",
    endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
    region_name=os.environ.get("S3_REGION_NAME"),
    addressing_style=os.environ.get("S3_ADDRESSING_STYLE"),
    access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
    secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
)
service._bucket = os.environ["BUCKET"]  # pylint: disable=protected-access

try:
    keys = service.list_keys("backups/")
except Exception as exc:  # noqa: BLE001  (any failure is a reachability failure)
    print(f"unreachable: {type(exc).__name__}")
    sys.exit(1)

print(f"reachable: {len(keys)} object(s) under backups/")
PROBE
  ); then
    check ok "S3 bucket '${S3_BUCKET_BACKUP}': ${S3_PROBE}"
  else
    check warn "S3 bucket '${S3_BUCKET_BACKUP}': ${S3_PROBE}"
  fi
else
  check fail "No backup destination configured (rclone remote or S3_BUCKET_BACKUP)"
fi

# 3. Last backup freshness
#
# Derived from the remote listing rather than a second independent probe, so
# the reported age cannot disagree with what was actually written.
LAST_TS=""
if [ "${BACKEND}" = "rclone" ] && [ -n "${REMOTE%%:*}" ]; then
  RCLONE_CHECK_TARGET="${REMOTE}"
  [[ "${REMOTE}" == *:* ]] || RCLONE_CHECK_TARGET="${REMOTE}:iqoqo_backups"
  if command -v rclone >/dev/null 2>&1; then
    # `lsl` output is "<size> <YYYY-MM-DD HH:MM:SS> <name>".
    LAST_TS=$(rclone lsl "${RCLONE_CHECK_TARGET}" 2>/dev/null | sort -k2,3 | tail -1 | awk '{print $2, $3}')
  fi
elif [ "${BACKEND}" = "s3" ] && [ -n "${S3_BUCKET_BACKUP:-}" ] && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
  if "${PYTHON_BIN}" -c "import boto3" >/dev/null 2>&1; then
    NEWEST_KEY=$(
      BUCKET="${S3_BUCKET_BACKUP}" "${PYTHON_BIN}" - <<'NEWEST' 2>/dev/null || true
import os

from app.core.s3_service import S3Service

service = S3Service(
    "backup",
    endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
    region_name=os.environ.get("S3_REGION_NAME"),
    addressing_style=os.environ.get("S3_ADDRESSING_STYLE"),
    access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
    secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
)
service._bucket = os.environ["BUCKET"]  # pylint: disable=protected-access

# The key basename embeds the timestamp cloud_backup.sh generated
# (iqoqo_backup_<YYYYmmdd_HHMMSS>.tar.gz), so the newest key by name is also
# the newest by time -- no extra HEAD request per object needed.
keys = [k for k in service.list_keys("backups/") if k.endswith(".tar.gz")]
if keys:
    print(max(keys))
NEWEST
    )
    if [ -n "${NEWEST_KEY}" ]; then
      # iqoqo_backup_<YYYYmmdd>_<HHMMSS>.tar.gz -> "YYYYmmdd HH:MM:SS"
      BASE=$(basename "${NEWEST_KEY}" .tar.gz)
      STAMP="${BASE#iqoqo_backup_}"
      STAMP="${STAMP//_/ }"
      LAST_TS="${STAMP:0:8} ${STAMP:9:2}:${STAMP:11:2}:${STAMP:13:2}"
    fi
  fi
fi

if [ -n "${LAST_TS}" ]; then
  LAST_EPOCH=$(date -d "${LAST_TS}" +%s 2>/dev/null || echo "")
  NOW_EPOCH=$(date +%s)
  if [ -z "${LAST_EPOCH}" ]; then
    check warn "Last ${JOB_TYPE}: found (${LAST_TS}) but its timestamp could not be parsed"
  else
    HOURS_AGO=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))
    if [ "${IS_ARCHIVE}" = true ]; then
      # Monthly archive threshold: fresh <= 35 days (840h), warn 35-45 days (1080h), stale > 45 days
      if [ "${HOURS_AGO}" -le 840 ]; then
        check ok "Last archive: $((HOURS_AGO / 24))d ago"
      elif [ "${HOURS_AGO}" -le 1080 ]; then
        check warn "Last archive: $((HOURS_AGO / 24))d ago (over 35 days)"
      else
        check fail "Last archive: $((HOURS_AGO / 24))d ago (STALE)"
      fi
    else
      if [ "${HOURS_AGO}" -le 24 ]; then
        check ok "Last backup: ${HOURS_AGO}h ago"
      elif [ "${HOURS_AGO}" -le 48 ]; then
        check warn "Last backup: ${HOURS_AGO}h ago (over 24h)"
      else
        check fail "Last backup: ${HOURS_AGO}h ago (STALE)"
      fi
    fi
  fi
elif [ "${BACKEND}" = "none" ]; then
  check warn "Last ${JOB_TYPE}: not checked (no destination configured)"
else
  check warn "Last ${JOB_TYPE}: none found on ${BACKEND}"
fi

# 4. Disk space
# MOD-OPS-14: use `df -P` (POSIX output format). Without it, GNU df wraps long
# device names onto a second line, which shifts every subsequent field by one
# and makes `awk 'NR==2 {print $4}'` read the wrong column — silently reporting
# a wrong free-space figure instead of failing. -P guarantees exactly one line
# of output per filesystem with stable field positions.
AVAIL=$(df -P "$(dirname "$0")/.." | awk 'NR==2 {print $4}')
if [ "${AVAIL}" -gt 1048576 ]; then
  check ok "Disk: $((AVAIL / 1024)) MB available"
else
  check warn "Disk: $((AVAIL / 1024)) MB available (low)"
fi

# 5. Script syntax
SCRIPT_DIR="$(dirname "$0")"
if bash -n "${SCRIPT_DIR}/cloud_backup.sh" 2>/dev/null; then
  check ok "Backup script: syntax OK"
else
  check fail "Backup script: syntax error"
fi

echo ""
if [ "${errors}" -eq 0 ]; then
  echo "All checks passed!"
else
  echo "${errors} check(s) failed."
fi

exit "${errors}"