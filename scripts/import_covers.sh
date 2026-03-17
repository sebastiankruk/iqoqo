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
# iqoqo - Server-side script to automate importing uploaded covers
# Usage: ./scripts/import_covers.sh [CONTAINER_NAME] [ARCHIVE_PATH]

# Default to your known preview container, override via arguments if needed
CONTAINER_NAME=${1:-iqoqo-preview-web-1}
ARCHIVE_PATH=${2:-/tmp/covers.tar.gz}
DEST_DIR="/usr/src/app/app/static/"

echo "📦 Starting cover import process for container: $CONTAINER_NAME"
echo "📂 Source archive: $ARCHIVE_PATH"

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "❌ Error: Archive not found at $ARCHIVE_PATH. Please upload it via SCP first."
    exit 1
fi

echo "1/4: Injecting archive into the container..."
# Using sudo based on your environment's Docker permissions
sudo docker cp "$ARCHIVE_PATH" "$CONTAINER_NAME:/tmp/covers.tar.gz"

echo "2/4: Extracting archive..."
sudo docker exec "$CONTAINER_NAME" bash -c "tar -xzvf /tmp/covers.tar.gz -C $DEST_DIR"

echo "3/4: Running rebind script..."
sudo docker exec "$CONTAINER_NAME" python -m scripts.rebind_covers

echo "4/4: Cleaning up temporary files inside container..."
sudo docker exec "$CONTAINER_NAME" rm /tmp/covers.tar.gz

echo "🗑️  (Optional) Removing local archive on host server..."
read -p "Delete $ARCHIVE_PATH on this server? (y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] && rm "$ARCHIVE_PATH" || echo "Archive kept on host."

echo "✅ Import complete!"
