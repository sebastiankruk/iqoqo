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
make preview-down DEPLOY_DIR="$DST_LOC"

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
make preview-down DEPLOY_DIR="$DST_LOC"

if [ "$SKIP_CLONE" != "1" ] && [ -n "$FEDERATION_PAIR" ] && [ "$FEDERATION_PAIR" != "0" ]; then
    echo "🧹 Resetting peer database volumes for clean paired federation preview..."
    docker volume rm -f iqoqo-preview_peer_postgres_data iqoqo-preview_peer_data 2>/dev/null || true
fi

make preview-up DEPLOY_DIR="$DST_LOC" FEDERATION_PAIR="$FEDERATION_PAIR"

# 5. Wait for preview backend and observability readiness before running make status
echo "Waiting for preview backend to become healthy..."
PREVIEW_READY=0
for i in $(seq 1 45); do
    if curl -s -f --max-time 2 "http://127.0.0.1:5001/api/health" >/dev/null 2>&1 || \
       curl -s -f --max-time 2 "http://127.0.0.1:8000/api/health" >/dev/null 2>&1 || \
       curl -s -f --max-time 2 "http://127.0.0.1:5002/api/health" >/dev/null 2>&1; then
        echo "✅ Preview backend healthy after ${i}s"
        PREVIEW_READY=1
        break
    fi
    sleep 1
done
if [ "$PREVIEW_READY" -ne 1 ]; then
    echo "💥 ERROR: Preview backend healthcheck timed out after 45s" >&2
    exit 1
fi

running_obs=$(docker ps --format '{{.Names}}' 2>/dev/null || true)
has_oo=0
has_otel=0
echo "$running_obs" | grep -q 'openobserve' && has_oo=1
echo "$running_obs" | grep -q 'otel-collector' && has_otel=1

if [ "$has_oo" -eq 1 ] || [ "$has_otel" -eq 1 ]; then
    echo "Waiting for OpenObserve & OTel Collector readiness..."
    oo_port="${OPENOBSERVE_HOST_PORT:-5080}"
    otel_http_port="${OTEL_HTTP_HOST_PORT:-4318}"
    if [ -f "$DST_LOC/.env" ]; then
        env_oo_port=$(grep -E '^OPENOBSERVE_HOST_PORT=' "$DST_LOC/.env" 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
        env_otel_port=$(grep -E '^OTEL_HTTP_HOST_PORT=' "$DST_LOC/.env" 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
        [ -n "$env_oo_port" ] && oo_port="$env_oo_port"
        [ -n "$env_otel_port" ] && otel_http_port="$env_otel_port"
    fi
    OBS_READY=0
    for j in $(seq 1 30); do
        oo_ok=1
        otel_ok=1
        if [ "$has_oo" -eq 1 ]; then
            oo_ok=0
            curl -s -f --max-time 2 "http://127.0.0.1:${oo_port}/healthz" >/dev/null 2>&1 && oo_ok=1
        fi
        if [ "$has_otel" -eq 1 ]; then
            otel_ok=0
            otel_code=$(curl -s --max-time 2 -o /dev/null -w '%{http_code}' "http://127.0.0.1:${otel_http_port}/v1/traces" 2>/dev/null || echo "000")
            case "$otel_code" in
                200|204|405) otel_ok=1 ;;
            esac
        fi
        if [ "$oo_ok" -eq 1 ] && [ "$otel_ok" -eq 1 ]; then
            echo "✅ Observability stack ready after ${j}s"
            OBS_READY=1
            break
        fi
        sleep 1
    done
    if [ "$OBS_READY" -ne 1 ]; then
        echo "💥 ERROR: Observability stack readiness timed out after 30s (oo_ok=${oo_ok}, otel_ok=${otel_ok})" >&2
        exit 1
    fi

    if [ "$has_oo" -eq 1 ] && [ -f "$DST_LOC/.env" ]; then
        oo_auth=$(grep -E '^OPENOBSERVE_BASIC_AUTH=' "$DST_LOC/.env" 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
        if [ -n "$oo_auth" ]; then
            oo_auth_code=$(curl -s --max-time 3 -o /dev/null -w '%{http_code}' -H "Authorization: Basic ${oo_auth}" "http://127.0.0.1:${oo_port}/api/default/streams" 2>/dev/null || echo "000")
            if [ "$oo_auth_code" = "401" ]; then
                echo "🔑 OpenObserve auth mismatch (HTTP 401); resetting OpenObserve auth state from $DST_LOC/.env..."
                MODE=preview DEPLOY_DIR="$DST_LOC" make monitoring-reset-auth
            fi
        fi
    fi
fi

# Reconcile cloned InstanceSettings rows encrypted with source SECRET_KEY
if [ -f "$DST_LOC/.env" ] && [ -f "$DST_LOC/docker-compose.prebuilt.yml" ]; then
    echo "🔐 Reconciling encrypted InstanceSettings with preview SECRET_KEY..."
    COMPOSE_PROJECT_NAME=iqoqo-preview APP_VERSION=preview docker compose --project-directory "$DST_LOC" --env-file "$DST_LOC/.env" -f "$DST_LOC/docker-compose.prebuilt.yml" exec -T web python3 -c "
import os
from cryptography.fernet import InvalidToken
from app import create_app
from app.db import db
from app.db.models import InstanceSettings
from app.db.settings import _get_fernet_cipher, encrypt_setting_value

app = create_app()
reencrypted = 0
cleared = 0
with app.app_context():
    cipher = _get_fernet_cipher()
    rows = db.session.execute(db.select(InstanceSettings)).scalars().all()
    for row in rows:
        if isinstance(row.value, dict) and row.value.get('_encrypted') is True and isinstance(row.value.get('ciphertext'), str):
            try:
                cipher.decrypt(row.value['ciphertext'].encode('utf-8'))
            except InvalidToken:
                env_val = os.environ.get(row.key)
                if env_val:
                    row.value = encrypt_setting_value(row.key, env_val)
                    reencrypted += 1
                else:
                    db.session.delete(row)
                    cleared += 1
    if reencrypted or cleared:
        db.session.commit()
print(f'✅ Encrypted settings reconciled (re-encrypted: {reencrypted}, cleared stale: {cleared})')
"
fi

make status preview

# 6. Run automated federation verification if federation pair is active
if [ -n "$FEDERATION_PAIR" ] && [ "$FEDERATION_PAIR" != "0" ]; then
    echo "🔗 Running automated federation preview verification..."
    bash scripts/verify_federation_preview.sh
fi
