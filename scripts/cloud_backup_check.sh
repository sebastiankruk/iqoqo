#!/bin/bash
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iQoQo Backup Health Check
# Usage: ./scripts/cloud_backup_check.sh [rclone_remote_name]
#
# Checks:
#   1. Cron job installed
#   2. Rclone remote configured and reachable
#   3. Last backup freshness (pass <24h, warn 24-48h, fail >48h)
#   4. Available disk space
#   5. Backup script syntax

set -euo pipefail

REMOTE="${1:-}"
if [ -z "${REMOTE}" ]; then
  REMOTE=$(grep -oP 'cloud_backup\.sh\s+\K\S+' /etc/cron.d/iqoqo-backup 2>/dev/null || echo "iqoqo-backup")
fi

errors=0

check() {
  local status="$1" msg="$2"
  case "${status}" in
    ok)  echo "  [OK]  ${msg}" ;;
    warn) echo "  [WARN] ${msg}" ;;
    fail) echo "  [FAIL] ${msg}"; errors=$((errors + 1)) ;;
  esac
}

echo "Checking iQoQo backup configuration (remote: ${REMOTE})..."
echo ""

# 1. Cron job
CRON_FILE="/etc/cron.d/iqoqo-backup"
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

# 2. Rclone remote
RCLONE_CMD="rclone"
if [ -n "${RCLONE_CONFIG:-}" ]; then
  RCLONE_CMD="rclone --config=${RCLONE_CONFIG}"
fi
REMOTE_NAME="${REMOTE%%:*}"
if [[ "${REMOTE}" == *":"* ]]; then
  RCLONE_CHECK_TARGET="${REMOTE}"
else
  RCLONE_CHECK_TARGET="${REMOTE}:iqoqo_backups"
fi

if ${RCLONE_CMD} listremotes 2>/dev/null | grep -q "^${REMOTE_NAME}:"; then
  check ok "Rclone remote '${REMOTE_NAME}': configured"
  if ${RCLONE_CMD} about "${REMOTE_NAME}:" 2>/dev/null >/dev/null; then
    check ok "Rclone remote '${REMOTE_NAME}': reachable"
  else
    check warn "Rclone remote '${REMOTE_NAME}': configured but unreachable"
  fi
else
  check fail "Rclone remote '${REMOTE_NAME}': not found"
fi

# 3. Last backup freshness
LAST_ENTRY=$(${RCLONE_CMD} lsl "${RCLONE_CHECK_TARGET}" 2>/dev/null | sort -k2,3 | tail -1)
if [ -n "${LAST_ENTRY}" ]; then
  LAST_TS=$(echo "${LAST_ENTRY}" | awk '{print $2, $3}')
  LAST_EPOCH=$(date -d "${LAST_TS}" +%s 2>/dev/null)
  NOW_EPOCH=$(date +%s)
  HOURS_AGO=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))
  if [ "${HOURS_AGO}" -le 24 ]; then
    check ok "Last backup: ${HOURS_AGO}h ago"
  elif [ "${HOURS_AGO}" -le 48 ]; then
    check warn "Last backup: ${HOURS_AGO}h ago (over 24h)"
  else
    check fail "Last backup: ${HOURS_AGO}h ago (STALE)"
  fi
else
  check warn "Last backup: none found on remote"
fi

# 4. Disk space
AVAIL=$(df "$(dirname "$0")/.." | awk 'NR==2 {print $4}')
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