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

RCLONE_REMOTE="${1:-iqoqo-backup}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/iqoqo_backup_${TIMESTAMP}"
ARCHIVE="${BACKUP_DIR}.tar.gz"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-iqoqo}"

echo "🗄️  Starting iQoQo backup (remote: ${RCLONE_REMOTE})..."
mkdir -p "${BACKUP_DIR}"

# 1. Dump PostgreSQL
echo "📦 Dumping PostgreSQL database..."
docker compose -f docker-compose.yml exec -T db \
    pg_dumpall -c -U "${POSTGRES_USER:-iqoqo}" \
    > "${BACKUP_DIR}/db_dump_${TIMESTAMP}.sql"

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
rclone copy "${ARCHIVE}" "${RCLONE_REMOTE}:/"

# 5. Cleanup
echo "🧹 Cleaning up local temp files..."
rm -rf "${BACKUP_DIR}" "${ARCHIVE}"

echo "✅ Backup completed successfully → ${RCLONE_REMOTE}:/"
