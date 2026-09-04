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
# iqoqo Multi-Image Docker Builder
# Builds backend, frontend, and nginx images locally with configurable tags.
# =============================================================================
set -e

TAG=""
PREFIX=""
VERSION=""

while [ $# -gt 0 ]; do
    case "$1" in
        --tag|-t)
            shift
            TAG="$1"
            ;;
        --prefix|-p)
            shift
            PREFIX="$1"
            ;;
        --version|-v)
            shift
            VERSION="$1"
            ;;
        --help|-h)
            echo "Usage: $0 [--tag <tag>] [--prefix <prefix>] [--version <version>]"
            echo "  --tag, -t     Tag to apply (e.g., 'preview', '0.7.17'). Defaults to version from pyproject.toml"
            echo "  --prefix, -p  Image prefix (e.g., 'ghcr.io/sebastiankruk/')"
            echo "  --version, -v Explicit version override for build arguments"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
    shift
done

# Navigate to project root if script is executed from scripts/
cd "$(dirname "$0")/.."

# Detect version from pyproject.toml if not explicitly supplied
if [ -z "$VERSION" ]; then
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
" 2>/dev/null || echo "0.0.0")
fi

# Default tag to version if not specified
if [ -z "$TAG" ]; then
    TAG="$VERSION"
    TAG_ARGS=(-t "${PREFIX}iqoqo-backend:${TAG}" -t "${PREFIX}iqoqo-backend:latest")
    FE_TAG_ARGS=(-t "${PREFIX}iqoqo-frontend:${TAG}" -t "${PREFIX}iqoqo-frontend:latest")
    NGINX_TAG_ARGS=(-t "${PREFIX}iqoqo-nginx:${TAG}" -t "${PREFIX}iqoqo-nginx:latest")
else
    TAG_ARGS=(-t "${PREFIX}iqoqo-backend:${TAG}")
    FE_TAG_ARGS=(-t "${PREFIX}iqoqo-frontend:${TAG}")
    NGINX_TAG_ARGS=(-t "${PREFIX}iqoqo-nginx:${TAG}")
fi

echo "🔨 Building iqoqo multi-image Docker suite"
echo "------------------------------------------"
echo "📦 Version: $VERSION"
echo "🏷️  Primary Tag: $TAG"
if [ -n "$PREFIX" ]; then
    echo "🏷️  Prefix: $PREFIX"
fi
echo ""

# 1. Build Backend (web & celery worker)
echo "🐳 [1/3] Building backend image..."
docker build \
    --build-arg APP_VERSION="$VERSION" \
    "${TAG_ARGS[@]}" \
    -f deploy/Dockerfile .
echo "✅ Backend image built successfully!"
echo ""

# 2. Build Frontend (Next.js standalone production runtime)
echo "🐳 [2/3] Building frontend image..."
docker build \
    --build-arg APP_VERSION="$VERSION" \
    --build-arg NEXT_PUBLIC_APP_VERSION="$VERSION" \
    "${FE_TAG_ARGS[@]}" \
    -f frontend/Dockerfile.prod ./frontend
echo "✅ Frontend image built successfully!"
echo ""

# 3. Build Nginx (Reverse proxy with embedded OTel module and virtual host routing)
echo "🐳 [3/3] Building nginx reverse-proxy image..."
docker build \
    "${NGINX_TAG_ARGS[@]}" \
    -f deploy/Dockerfile.nginx .
echo "✅ Nginx image built successfully!"
echo ""

echo "🎉 All iqoqo container images built successfully!"
echo "Inspect images with: docker images | grep iqoqo"
