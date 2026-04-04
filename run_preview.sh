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

# Stop on first error
set -e

# Export the specific environment file to inject into the web container
export ENV_FILE=".env.preview"

echo "🚀 Deploying iqoqo PREVIEW environment with ENV_FILE=$ENV_FILE..."

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE file not found."
    echo "   Please copy .env.preview.example to $ENV_FILE and configure your secrets."
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
    export APP_VERSION="${VERSION:-preview}"
fi

# Optional: Stop previous instances if requested
if [[ "$*" == *"--clean"* ]]; then
    echo "🧹 Stopping and removing previous preview instances..."
    docker compose -p iqoqo-preview -f docker-compose.prod.yml --env-file "$ENV_FILE" down --remove-orphans
fi

# Start containers using base + preview overrides
echo "🚀 Starting iqoqo preview deployment (Version: $APP_VERSION)..."
docker compose -p iqoqo-preview -f docker-compose.prod.yml --env-file "$ENV_FILE" up -d --build

# We no longer need the manual migration command here as the 'web' service handles it on startup
# with the 'python scripts/fix_alembic.py && flask db upgrade' command.

echo "✅ Preview environment started successfully!"
echo "   Note: It may take a moment for the database to be ready and migrations to complete."
echo "🌐 Local access: http://localhost:8081"
