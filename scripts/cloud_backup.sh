#!/bin/bash
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iQoQo Cloud Backup Script
# Usage: ./scripts/cloud_backup.sh [RCLONE_REMOTE_NAME]
# Requires: rclone installed and configured on the host system.
#
# Backs up:
#   1. PostgreSQL full database dump (pg_dumpall)
#   2. Uploaded asset volumes (covers/, data/)
# Then compresses and syncs to rclone remote.

set -euo pipefail

if [ -f "$(dirname "$0")/../.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$(dirname "$0")/../.env"
    set +a
fi

RCLONE_REMOTE="${1:-${RCLONE_REMOTE_FAST:-iqoqo-backup}}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/iqoqo_backup_${TIMESTAMP}"
ARCHIVE="${BACKUP_DIR}.tar.gz"


echo "🗄️  Starting iQoQo backup (remote: ${RCLONE_REMOTE})..."
mkdir -p "${BACKUP_DIR}"

# 1. Dump PostgreSQL
DB_DUMP_FILE="${BACKUP_DIR}/db_dump_${TIMESTAMP}.sql"
DB_CONTAINER=$(docker ps --filter "name=db" --format "{{.Names}}" | head -1)
if [ -n "${DB_CONTAINER}" ]; then
    docker exec -i "${DB_CONTAINER}" pg_dumpall -c -U "${POSTGRES_USER:-iqoqo}" > "${DB_DUMP_FILE}"
else
    COMPOSE_SPEC="${COMPOSE_FILE:-docker-compose.yml}"
    docker compose -f "${COMPOSE_SPEC}" exec -T db \
        pg_dumpall -c -U "${POSTGRES_USER:-iqoqo}" \
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

# 4. Sync to cloud
echo "☁️  Syncing to ${RCLONE_REMOTE}..."
if [[ "${RCLONE_REMOTE}" == *":"* ]]; then
    RCLONE_TARGET="${RCLONE_REMOTE}"
else
    RCLONE_TARGET="${RCLONE_REMOTE}:iqoqo_backups"
fi

if rclone copy "${ARCHIVE}" "${RCLONE_TARGET}" --s3-no-check-bucket; then
    echo "✅ Backup synced → ${RCLONE_TARGET}"
else
    echo "❌ Cloud sync failed! Archive preserved at: ${ARCHIVE}" >&2
    exit 1
fi

# 5. Cleanup only on successful sync
echo "🧹 Cleaning up local temp files..."
rm -rf "${BACKUP_DIR}" "${ARCHIVE}"

echo "✅ Backup completed successfully"
