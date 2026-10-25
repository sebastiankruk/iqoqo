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
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANDIDATE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$CANDIDATE_ROOT/pyproject.toml" ] && [ -f "$CANDIDATE_ROOT/deploy/Dockerfile" ]; then
    REPO_ROOT="$CANDIDATE_ROOT"
elif [ -n "${IQOQO_DEV_DIR:-}" ] && [ -f "$IQOQO_DEV_DIR/pyproject.toml" ]; then
    REPO_ROOT="$IQOQO_DEV_DIR"
elif [ -f "/home/sebastiankruk/Development/iqoqo/pyproject.toml" ]; then
    REPO_ROOT="/home/sebastiankruk/Development/iqoqo"
else
    echo "💥 ERROR: Cannot find iqoqo source checkout containing deploy/Dockerfile." >&2
    echo "Please set IQOQO_DEV_DIR or run from the development repository." >&2
    exit 1
fi

cd "$REPO_ROOT"

# Parameter defaults (overridable via env or CLI flags)
SRC_HOST="${SRC_HOST:-${CLONE_SRC_HOST:-prod.iqoqo.cc}}"
SRC_LOC="${SRC_LOC:-${CLONE_SRC_LOC:-/opt/iqoqo}}"
SRC_NAME="${SRC_NAME:-${CLONE_SRC_NAME:-prod}}"
DST_LOC="${DST_LOC:-${CLONE_DST_LOC:-/opt/pre.iqoqo}}"
DST_NAME="${DST_NAME:-${CLONE_DST_NAME:-preview}}"		
SKIP_CLONE="${SKIP_CLONE:-0}"
FEDERATION_PAIR="${FEDERATION_PAIR:-0}"

while [ $# -gt 0 ]; do
    case "$1" in
        --src-host)
            shift
            SRC_HOST="${1:-}"
            ;;
        --src-host=*)
            SRC_HOST="${1#*=}"
            ;;
        --src-loc)
            shift
            SRC_LOC="$1"
            ;;
        --src-loc=*)
            SRC_LOC="${1#*=}"
            ;;
        --src-name)
            shift
            SRC_NAME="$1"
            ;;
        --src-name=*)
            SRC_NAME="${1#*=}"
            ;;
        --dst-loc)
            shift
            DST_LOC="$1"
            ;;
        --dst-loc=*)
            DST_LOC="${1#*=}"
            ;;
        --dst-name)
            shift
            DST_NAME="$1"
            ;;
        --dst-name=*)
            DST_NAME="${1#*=}"
            ;;
        --skip-clone)
            SKIP_CLONE="1"
            ;;
        --federation-pair|--federation)
            FEDERATION_PAIR="1"
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --src-host <host>     Source host for prod clone (default: \$SRC_HOST or h.kruk.me)"
            echo "  --src-loc <path>      Source location (default: \$SRC_LOC or /opt/iqoqo)"
            echo "  --src-name <name>     Source stack name (default: \$SRC_NAME or prod)"
            echo "  --dst-loc <path>      Destination location (default: \$DST_LOC or /opt/pre.iqoqo)"
            echo "  --dst-name <name>     Destination stack name (default: \$DST_NAME or preview)"
            echo "  --skip-clone          Skip database and volume clone"
            echo "  --federation-pair     Start paired federation preview stack (peer-web, peer-frontend, peer-db)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            ;;
    esac
    shift
done

# 1. Verify project version
make version
make preview-down

# 2. Build local Docker images tagged with 'preview'
echo "🔨 Building preview Docker images..."
if ! make docker-build-preview; then
    echo "💥 ERROR: Preview Docker image build failed! Stop immediately so old container does not run." >&2
    exit 1
fi

# 3. Clone database and assets unless skipped
if [ "$SKIP_CLONE" = "1" ]; then
    echo "Skipping cloning (--skip-clone set)"
else
    echo "📦 Cloning from ${SRC_HOST:+${SRC_HOST}:}${SRC_LOC} (${SRC_NAME}) to ${DST_LOC} (${DST_NAME})..."
    clone_args=(
        "src_loc=${SRC_LOC}"
        "src_name=${SRC_NAME}"
        "dst_loc=${DST_LOC}"
        "dst_name=${DST_NAME}"
    )
    if [ -n "$SRC_HOST" ]; then
        clone_args+=("src_host=${SRC_HOST}")
    fi
    FORCE="${FORCE:-0}" make clone "${clone_args[@]}"
fi

# 4. Restart preview stack cleanly (optionally with federation peer)
make preview-down
make preview-up FEDERATION_PAIR="$FEDERATION_PAIR"

# 5. Verify final version
echo "waiting 30 seconds for iqoqo to start"
sleep 30
make status preview

# 6. Run automated federation verification if federation pair is active
if [ -n "$FEDERATION_PAIR" ] && [ "$FEDERATION_PAIR" != "0" ]; then
    echo "🔗 Running automated federation preview verification..."
    bash scripts/verify_federation_preview.sh
fi
