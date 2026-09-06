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
# =============================================================================
# Exit immediately if a command exits with a non-zero status
set -e

echo "🔨 iqoqo local docker build tester"
echo "-----------------------------------"

# Extract version using Python (matching your new CI pipeline)
echo "📦 Extracting version from pyproject.toml..."
PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi
VERSION=$($PYTHON_BIN -c "
try:
    import tomllib
    with open('pyproject.toml', 'rb') as f:
        print(tomllib.load(f)['project']['version'])
except Exception:
    import re
    with open('pyproject.toml') as f:
        m = re.search(r'version\s*=\s*\"([^\"]+)\"', f.read())
        print(m.group(1) if m else '0.0.0')
")
echo "📌 Version found: v$VERSION"
echo ""

# Build Backend
echo "🐳 Building iqoqo-backend:v$VERSION..."
docker build \
  -t "iqoqo-backend:v$VERSION" \
  -t iqoqo-backend:latest \
  -f deploy/Dockerfile .
echo "✅ Backend build successful!"
echo ""

# Build Frontend
echo "🐳 Building iqoqo-frontend:v$VERSION..."
docker build \
  -t "iqoqo-frontend:v$VERSION" \
  -t iqoqo-frontend:latest \
  -f frontend/Dockerfile.prod ./frontend
echo "✅ Frontend build successful!"
echo ""

# Build Nginx
echo "🐳 Building iqoqo-nginx:v$VERSION..."
docker build \
  -t "iqoqo-nginx:v$VERSION" \
  -t iqoqo-nginx:latest \
  -f deploy/Dockerfile.nginx .
echo "✅ Nginx build successful!"
echo ""

echo "🎉 All local builds completed successfully!"
echo "You can check your images by running: docker images | grep iqoqo"
