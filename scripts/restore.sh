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
# iQoQo Disaster Recovery Restore Script
# Usage: ./scripts/restore.sh <archive_tar_gz> [--yes]
#
# Restores:
#   1. PostgreSQL full database dump (including public, auth, social, federation schemas)
#   2. Uploaded assets (covers, gallery, raw_covers)
#   3. Instance cryptographic keys (data/federation_keys with 0700/0600 permissions)

set -euo pipefail

log() {
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[${ts}] $*"
}

log_err() {
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[${ts}] $*" >&2
}

# Enforce owner-only permissions for extracted files
umask 077

ARCHIVE_PATH=""
FORCE_YES=false

for arg in "$@"; do
    case "${arg}" in
        --yes|-y)
            FORCE_YES=true
            ;;
        *)
            if [ -z "${ARCHIVE_PATH}" ]; then
                ARCHIVE_PATH="${arg}"
            fi
            ;;
    esac
done

if [ -z "${ARCHIVE_PATH}" ]; then
    log_err "❌ Usage: $0 <path_to_backup_archive.tar.gz> [--yes]"
    exit 1
fi

if [ ! -f "${ARCHIVE_PATH}" ]; then
    log_err "❌ Error: Backup archive not found: ${ARCHIVE_PATH}"
    exit 1
fi

# Load environment configuration if available
ORIG_POSTGRES_USER="${POSTGRES_USER:-}"
ORIG_POSTGRES_DB="${POSTGRES_DB:-}"
if [ -f "$(dirname "$0")/../.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$(dirname "$0")/../.env"
    set +a
fi
if [ -n "${ORIG_POSTGRES_USER}" ]; then
    POSTGRES_USER="${ORIG_POSTGRES_USER}"
fi
if [ -n "${ORIG_POSTGRES_DB}" ]; then
    POSTGRES_DB="${ORIG_POSTGRES_DB}"
fi

EFFECTIVE_PG_USER="${POSTGRES_USER:-iqoqo}"
EFFECTIVE_PG_DB="${POSTGRES_DB:-iqoqo}"
CURRENT_ENV="${FLASK_ENV:-${APP_ENV:-development}}"

# Production operational guard
if [ "${CURRENT_ENV}" = "production" ] && [ "${FORCE_YES}" != true ]; then
    echo "⚠️  WARNING: Restoring backup in PRODUCTION environment will overwrite existing database and assets!"
    echo "To confirm, please type the target database name ('${EFFECTIVE_PG_DB}'): "
    read -r CONFIRMED_DB
    if [ "${CONFIRMED_DB}" != "${EFFECTIVE_PG_DB}" ]; then
        log_err "❌ Confirmation failed. Aborting restore."
        exit 1
    fi
elif [ "${FORCE_YES}" != true ] && [ -t 0 ]; then
    read -r -p "⚠️  Proceed with restore from '${ARCHIVE_PATH}'? [y/N] " CONFIRM
    if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
        log "Restore cancelled by user."
        exit 0
    fi
fi

TEMP_RESTORE_DIR=$(mktemp -d "/tmp/iqoqo_restore_XXXXXX")
cleanup() {
    rm -rf "${TEMP_RESTORE_DIR}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

log "📦 Extracting top-level archive: ${ARCHIVE_PATH}..."
tar -xzf "${ARCHIVE_PATH}" -C "${TEMP_RESTORE_DIR}"

# Locate the nested backup directory
UNPACKED_DIR=$(find "${TEMP_RESTORE_DIR}" -mindepth 1 -maxdepth 1 -type d -name "iqoqo_backup_*" | head -1)
if [ -z "${UNPACKED_DIR}" ] || [ ! -d "${UNPACKED_DIR}" ]; then
    UNPACKED_DIR="${TEMP_RESTORE_DIR}"
fi

# 1. Restore PostgreSQL database dump
DB_DUMP_FILE=$(find "${UNPACKED_DIR}" -maxdepth 1 -type f -name "db_dump_*.sql" | head -1)
if [ -n "${DB_DUMP_FILE}" ] && [ -s "${DB_DUMP_FILE}" ]; then
    log "🔍 Validating database dump file: $(basename "${DB_DUMP_FILE}")..."
    if ! grep -q "CREATE\|INSERT\|ALTER\|SET" "${DB_DUMP_FILE}" 2>/dev/null; then
        log_err "❌ Error: Database dump appears invalid (no SQL statements found). Aborting restore."
        exit 1
    fi

    log "📊 Resolving database container..."
    DB_CONTAINER=$(docker ps --filter "name=iqoqo-db" --filter "status=running" --format "{{.Names}}" 2>/dev/null | head -1 || true)
    if [ -n "${DB_CONTAINER}" ]; then
        log "Restoring database dump via container ${DB_CONTAINER}..."
        docker exec -i "${DB_CONTAINER}" sh -c "PGHOST=/var/run/postgresql psql -U '${EFFECTIVE_PG_USER}' -d postgres" < "${DB_DUMP_FILE}"
    else
        log "Restoring database dump via docker compose..."
        COMPOSE_SPEC="${COMPOSE_FILE:-docker-compose.yml}"
        docker compose -f "${COMPOSE_SPEC}" exec -T db sh -c "PGHOST=/var/run/postgresql psql -U '${EFFECTIVE_PG_USER}' -d postgres" < "${DB_DUMP_FILE}"
    fi
    log "✅ Database dump restored successfully."
else
    log_err "⚠️  No valid db_dump_*.sql found in archive; skipping database restore."
fi

# 2. Restore asset tarballs
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${PROJECT_ROOT}"

while IFS= read -r -d '' asset_archive; do
    [ -z "${asset_archive}" ] && continue
    asset_base=$(basename "${asset_archive}")
    log "📁 Restoring asset archive: ${asset_base}..."
    tar -xzf "${asset_archive}" --no-same-owner -C "${PROJECT_ROOT}"
done < <(find "${UNPACKED_DIR}" -maxdepth 1 -type f -name "*_*.tar.gz" -print0 2>/dev/null || true)

# 3. Enforce strict permissions on restored federation keys
if [ -d "${PROJECT_ROOT}/data/federation_keys" ]; then
    log "🔒 Enforcing secure permissions on data/federation_keys..."
    chmod 0700 "${PROJECT_ROOT}/data/federation_keys"
    find "${PROJECT_ROOT}/data/federation_keys" -type f -exec chmod 0600 {} + 2>/dev/null || true
    log "✅ Federation keys restored with 0700 directory and 0600 file permissions."
fi

log "🎉 Disaster recovery restore completed successfully."
