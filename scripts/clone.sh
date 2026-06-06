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
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#

set -eo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <source_location> <source_name> <destination_location> <destination_name>"
    echo "Example: $0 /opt/iqoqo.cc prod /opt/pre.iqoqo.cc preview"
    exit 1
fi

SRC_DIR="$1"
SRC_NAME="$2"
DST_DIR="$3"
DST_NAME="$4"

# Validate directories
if [ ! -d "$SRC_DIR" ]; then
    echo "❌ Error: Source directory '$SRC_DIR' does not exist."
    exit 1
fi

if [ ! -d "$DST_DIR" ]; then
    echo "❌ Error: Destination directory '$DST_DIR' does not exist."
    exit 1
fi

SRC_ENV="${SRC_DIR}/.env.${SRC_NAME}"
DST_ENV="${DST_DIR}/.env.${DST_NAME}"

if [ ! -f "$SRC_ENV" ]; then
    echo "❌ Error: Source env file '$SRC_ENV' does not exist."
    exit 1
fi

if [ ! -f "$DST_ENV" ]; then
    echo "❌ Error: Destination env file '$DST_ENV' does not exist."
    exit 1
fi

# Load DB config from env files
get_env_var() {
    local file="$1"
    local var="$2"
    local default="$3"
    local val
    val=$(grep -E "^${var}=" "$file" | cut -d'=' -f2- | tr -d '"'\' | tr -d '\r')
    echo "${val:-$default}"
}

SRC_POSTGRES_USER=$(get_env_var "$SRC_ENV" "POSTGRES_USER" "iqoqo")
SRC_POSTGRES_DB=$(get_env_var "$SRC_ENV" "POSTGRES_DB" "iqoqo")

DST_POSTGRES_USER=$(get_env_var "$DST_ENV" "POSTGRES_USER" "iqoqo")
DST_POSTGRES_DB=$(get_env_var "$DST_ENV" "POSTGRES_DB" "iqoqo")

# Determine compose project names
SRC_PROJECT="iqoqo-${SRC_NAME}"
if [ "$SRC_NAME" = "prod" ]; then
    SRC_PROJECT="iqoqo"
fi

DST_PROJECT="iqoqo-${DST_NAME}"
if [ "$DST_NAME" = "prod" ]; then
    DST_PROJECT="iqoqo"
fi

# Find source database container
echo "🔍 Finding source database container for project '$SRC_PROJECT'..."
SRC_DB_CONTAINER=$(
    cd "$SRC_DIR"
    export ENV_FILE=".env.${SRC_NAME}"
    docker compose -p "$SRC_PROJECT" --env-file ".env.${SRC_NAME}" ps -q db 2>/dev/null
)

if [ -z "$SRC_DB_CONTAINER" ]; then
    echo "❌ Error: Source database container is not running. Please make sure '$SRC_NAME' environment is running."
    exit 1
fi

# Start destination database container
echo "🚀 Ensuring destination database container is running for project '$DST_PROJECT'..."
(
    cd "$DST_DIR"
    export ENV_FILE=".env.${DST_NAME}"
    docker compose -p "$DST_PROJECT" --env-file ".env.${DST_NAME}" up -d db
)

# Wait for destination database to be ready
echo "⏳ Waiting for destination database to be ready..."
DST_READY=false
for i in {1..30}; do
    DST_DB_CONTAINER=$(
        cd "$DST_DIR"
        export ENV_FILE=".env.${DST_NAME}"
        docker compose -p "$DST_PROJECT" --env-file ".env.${DST_NAME}" ps -q db 2>/dev/null
    )
    if [ -n "$DST_DB_CONTAINER" ]; then
        if docker exec "$DST_DB_CONTAINER" pg_isready -U "$DST_POSTGRES_USER" -d "$DST_POSTGRES_DB" &>/dev/null; then
            DST_READY=true
            break
        fi
    fi
    sleep 1
done

if [ "$DST_READY" = false ]; then
    echo "❌ Error: Destination database failed to become ready."
    exit 1
fi

# Terminate active connections, drop and recreate destination database, then dump and import
echo "🔒 Terminating existing connections to destination DB '$DST_POSTGRES_DB'..."
docker exec -i "$DST_DB_CONTAINER" psql -U "$DST_POSTGRES_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$DST_POSTGRES_DB' AND pid <> pg_backend_pid();" || true

echo "🗑️ Dropping and recreating destination database '$DST_POSTGRES_DB'..."
docker exec -i "$DST_DB_CONTAINER" psql -U "$DST_POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $DST_POSTGRES_DB;"
docker exec -i "$DST_DB_CONTAINER" psql -U "$DST_POSTGRES_USER" -d postgres -c "CREATE DATABASE $DST_POSTGRES_DB;"

echo "📥 Cloning database data..."
docker exec -i "$SRC_DB_CONTAINER" pg_dump -U "$SRC_POSTGRES_USER" --no-owner --no-privileges "$SRC_POSTGRES_DB" | \
  docker exec -i "$DST_DB_CONTAINER" psql -U "$DST_POSTGRES_USER" -d "$DST_POSTGRES_DB"

echo "✅ Database cloned successfully!"

# Sync static assets (covers and gallery)
echo "🖼️ Syncing images (covers and gallery)..."
for dir in "covers" "gallery"; do
    SRC_STATIC_DIR="${SRC_DIR}/app/static/${dir}"
    DST_STATIC_DIR="${DST_DIR}/app/static/${dir}"
    if [ -d "$SRC_STATIC_DIR" ]; then
        mkdir -p "$DST_STATIC_DIR"
        echo "🔄 Syncing static/${dir}..."
        if command -v rsync &>/dev/null; then
            rsync -a --delete "${SRC_STATIC_DIR}/" "${DST_STATIC_DIR}/"
        else
            cp -a "${SRC_STATIC_DIR}/." "${DST_STATIC_DIR}/"
        fi
    else
        echo "⚠️ Warning: Source static directory '$SRC_STATIC_DIR' does not exist, skipping."
    fi
done

echo "🎉 Data clone complete from '$SRC_NAME' to '$DST_NAME'!"
