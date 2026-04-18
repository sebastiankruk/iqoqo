#!/bin/bash
# Production Deployment Script
#
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

set -e

echo "🚀 Deploying iqoqo PRODUCTION environment..."

# 1. Check for configuration
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found."
    echo "   Please copy .env.example to .env and configure your secrets."
    exit 1
fi

# 1a. Load and validate environment variables
set -o allexport
source .env
set +o allexport

REQUIRED_VARS=("DATABASE_URL" "REDIS_URL" "SECRET_KEY" "AUTH_SECRET")
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables in .env: ${MISSING_VARS[*]}"
    exit 1
fi

# Activate Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Set APP_VERSION if not already set
if [ -z "$APP_VERSION" ]; then
    VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb')).get('project', {}).get('version'))")
    export APP_VERSION="${VERSION:-prod}"
fi

# Optional: Stop previous instances if requested
if [[ "$*" == *"--clean"* ]]; then
    echo "🧹 Stopping and removing previous production instances..."
    docker compose -f docker-compose.prod.yml down --remove-orphans
fi

# 1b. Ensure database is running (start db first for migration check)
echo "🔧 Checking database status..."
docker compose -f docker-compose.prod.yml up -d db redis

# 1c. Wait for DB to be ready
echo "⏳ Waiting for database to be ready..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" &>/dev/null; then
        echo "✅ Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Database failed to become ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# 1d. Check current migration state
# Use -At to get one row per line (unaligned, tuple-only) and capture all rows.
# If multiple rows are returned (multi-head state), warn rather than concatenate.
MIGRATION_ROWS=$(docker compose -f docker-compose.prod.yml exec -T db psql -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" -At -c "SELECT version_num FROM alembic_version;" 2>/dev/null)
MIGRATION_COUNT=$(echo "$MIGRATION_ROWS" | grep -c '[^[:space:]]' || true)

if [ "$MIGRATION_COUNT" -gt 1 ]; then
    echo "⚠️  WARNING: Multiple Alembic heads detected in the database:"
    echo "$MIGRATION_ROWS" | sed 's/^/   /'
    CURRENT_MIGRATION=""
elif [ "$MIGRATION_COUNT" -eq 1 ]; then
    CURRENT_MIGRATION=$(echo "$MIGRATION_ROWS" | tr -d '[:space:]')
else
    CURRENT_MIGRATION=""
fi

# Get expected migration head(s) from Alembic itself (most reliable method)
EXPECTED_HEADS=$(python3 -c "
from alembic.script import ScriptDirectory
try:
    heads = ScriptDirectory('migrations').get_heads()
    print(' '.join(heads))
except Exception:
    print('')
" 2>/dev/null || echo "")

HEAD_COUNT=$(echo "$EXPECTED_HEADS" | wc -w)

if [ "$HEAD_COUNT" -eq 1 ]; then
    EXPECTED_VERSION="$EXPECTED_HEADS"
elif [ "$HEAD_COUNT" -gt 1 ]; then
    echo "⚠️  WARNING: Multiple Alembic heads detected in the source code scripts: $EXPECTED_HEADS"
    EXPECTED_VERSION=""
else
    EXPECTED_VERSION=""
fi

if [ -n "$CURRENT_MIGRATION" ] && [ -n "$EXPECTED_VERSION" ]; then
    if [ "$CURRENT_MIGRATION" != "$EXPECTED_VERSION" ]; then
        echo "⚠️  WARNING: Database migration mismatch!"
        echo "   Current:  $CURRENT_MIGRATION"
        echo "   Expected: $EXPECTED_VERSION"
        echo "   Running migrations to bring DB up to date..."
    else
        echo "✅ Database migration state: $CURRENT_MIGRATION"
    fi
else
    echo "ℹ️  Could not determine migration state (current: '$CURRENT_MIGRATION', expected: '$EXPECTED_VERSION')"
fi

# Optional: Create DB backup before migrations
if [[ "$*" == *"--backup"* ]]; then
    BACKUP_FILE="exports/pre_deploy_backup_$(date +%Y%m%d_%H%M%S).sql"
    echo "📦 Creating pre-deploy backup: $BACKUP_FILE"
    mkdir -p exports
    docker compose -f docker-compose.prod.yml exec -T db pg_dump -U "${POSTGRES_USER:-iqoqo}" "${POSTGRES_DB:-iqoqo}" > "$BACKUP_FILE" || echo "⚠️  Backup failed, continuing..."
fi

# 2. Build and Start Services
echo "🚀 Starting iqoqo production deployment (Version: $APP_VERSION)..."
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo "✅ Deployment successful!"
echo "   Note: It may take a moment for the database to be ready and migrations to complete."
echo "🌍 Nginx is listening on port ${NGINX_PORT:-8000}"
