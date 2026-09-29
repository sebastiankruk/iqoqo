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
# iQoQo Cloud Backup Cron Management
# Usage: ./scripts/cloud_backup_cron.sh install [rclone_remote]
#        ./scripts/cloud_backup_cron.sh uninstall
#
# The optional remote argument selects the rclone backend, exactly as it always
# has. An S3-compatible backend is available too (S3_BACKEND=s3 plus
# S3_BUCKET_BACKUP and AWS_* credentials in the project .env), and
# cloud_backup.sh picks whichever is configured.

set -euo pipefail

CMD="${1:-}"
REMOTE="${2:-${RCLONE_REMOTE_FAST:-}}"

# Resolve a destination the same way cloud_backup.sh does, so `install` and the
# nightly job can never disagree about where the backup goes.
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
if [ -f "${ENV_FILE}" ]; then
    set -a
    # The path is a variable resolved at runtime, so shellcheck cannot follow it.
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
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
        # cloud_backup.sh: .env.example ships a default remote name, and that
        # must not hijack an S3-only deployment.
        if [ -f "${RCLONE_CONFIG:-${HOME}/.config/rclone/rclone.conf}" ]; then
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

# Fail early with an actionable message rather than installing a cron job that
# will fail silently at 03:00. cloud_backup.sh performs the same checks, but a
# broken nightly backup is only discovered when someone needs it.
if [ "${BACKEND}" = "rclone" ]; then
    if ! command -v rclone >/dev/null 2>&1; then
        echo "ERROR: rclone is not installed but is the selected backend." >&2
        echo "       Install it, or set S3_BACKEND=s3 to use S3-compatible storage." >&2
        exit 1
    fi
    # A named remote must actually exist; a default remote only needs the config.
    if [ -n "${REMOTE}" ] && ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE%%:*}:"; then
        echo "ERROR: Remote '${REMOTE}' not found" >&2
        echo "       List configured remotes with: rclone listremotes" >&2
        exit 1
    fi
elif [ "${BACKEND}" = "s3" ]; then
    if [ -z "${S3_BUCKET_BACKUP:-}" ]; then
        echo "ERROR: S3_BUCKET_BACKUP is not set in ${ENV_FILE:-.env}." >&2
        echo "       Add S3_BUCKET_BACKUP along with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY." >&2
        exit 1
    fi
    if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
        echo "ERROR: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must both be set in ${ENV_FILE:-.env}." >&2
        exit 1
    fi
else
    echo "ERROR: no backup destination is configured." >&2
    echo "       Either run 'rclone config' and name a remote, or set in ${ENV_FILE:-.env}:" >&2
    echo "         S3_BUCKET_BACKUP=<bucket>" >&2
    echo "         AWS_ACCESS_KEY_ID=<key>" >&2
    echo "         AWS_SECRET_ACCESS_KEY=<secret>" >&2
    exit 1
fi

case "${CMD}" in
  install)
    # The remote is only passed through for the rclone backend. Under S3 the
    # variables in .env are the configuration, and passing a stray argument
    # would switch cloud_backup.sh back to rclone at 03:00.
    CRON_CMD="./scripts/cloud_backup.sh"
    [ "${BACKEND}" = "rclone" ] && [ -n "${REMOTE}" ] && CRON_CMD="${CRON_CMD} ${REMOTE}"

    if [ "${BACKEND}" = "rclone" ]; then
        echo "Installing daily 03:00 cron job (backend: rclone, remote: ${REMOTE:-default})..."
    else
        echo "Installing daily 03:00 cron job (backend: s3, bucket: ${S3_BUCKET_BACKUP})..."
    fi
    echo "0 3 * * * root cd ${PROJECT_DIR} && ${CRON_CMD} >> /var/log/iqoqo_backup.log 2>&1" | \
      docker run --rm -i -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c 'cat > /etc/cron.d/iqoqo-backup'
    echo "Done. Next run: tonight at 03:00."
    ;;
  uninstall)
    echo "Removing iQoQo backup cron job..."
    docker run --rm -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c 'rm -f /etc/cron.d/iqoqo-backup'
    echo "Done."
    ;;
  *)
    echo "Usage: $0 <install|uninstall> [rclone_remote]" >&2
    echo "  install [remote] - Install daily 03:00 cron job" >&2
    echo "  uninstall        - Remove cron job" >&2
    exit 1
    ;;
esac
