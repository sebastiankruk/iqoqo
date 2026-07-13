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
# iqoqo Unified Management Script
#
# Usage: ./run.sh [mode] [--clean] [--backup] [--tunnel] [--key-rotate]
#
# Modes:
#   dev      (default) Run Flask, Celery, and Next.js as local processes.
#            Only db and redis are started in Docker.
#   ANYTHING else uses full Docker Compose (e.g., prod, preview).
#
# Options:
#   --clean       Stop and remove previous instances/containers, and rotate keys.
#   --key-rotate  Force rotation of all security keys (SECRET_KEY, JWT_SECRET_KEY, AUTH_SECRET).
#   --backup      Create a pre-deployment database backup (Docker modes only).
#   --tunnel      Load dev.iqoqo.cc configuration (dev mode only).

# 0. Set Mode and Parameters
MODE="dev"
MODE_SET=false
EXTRA_ARGS=()
TUNNEL=false
CLEAN=false
BACKUP=false
PREBUILT=false
STOP=false
ROTATE_FORCE=false
VALIDATE_ONLY=false
CUSTOM_VERSION=""

# Robust argument parsing
while [ $# -gt 0 ]; do
    case "$1" in
        dev|preview|prod)
            MODE="$1"
            MODE_SET=true
            ;;
        --tunnel)
            TUNNEL=true
            ;;
        --clean)
            CLEAN=true
            ;;
        --rotate|--key-rotate)
            ROTATE_FORCE=true
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            ;;
        --backup)
            BACKUP=true
            ;;
        --prebuilt)
            PREBUILT=true
            ;;
        --version)
            shift
            CUSTOM_VERSION="$1"
            ;;
        --stop)
            STOP=true
            ;;
        *)
            # Non-flag positional arg (if first) is treated as mode
            if [[ "$1" != -* ]] && [[ "$MODE_SET" = false ]]; then
                MODE="$1"
                MODE_SET=true
            else
                EXTRA_ARGS+=("$1")
            fi
            ;;
    esac
    shift
done

echo "🚀 iqoqo Management: Entering mode '$MODE'..."

# Ensure we are in the project root
cd "$(dirname "$0")" || exit 1

# Helper function to update or append environment variables in env files
update_env_var() {
    local file="$1"
    local key="$2"
    local val="$3"
    if [ ! -f "$file" ]; then
        touch "$file"
    fi
    # Delete existing entry if present, to avoid duplicates
    if grep -q "^${key}=" "$file"; then
        grep -v "^${key}=" "$file" > "${file}.tmp"
        mv "${file}.tmp" "$file"
    fi
    echo "${key}=\"${val}\"" >> "$file"
}

# Auto-generate or rotate keys in production/preview modes
auto_generate_or_rotate_keys() {
    local target_file=".env"
    if [ -f ".env.$MODE" ]; then
        target_file=".env.$MODE"
    fi

    local current_key="${SECRET_KEY}"
    local last_rotated="${SECRET_KEY_LAST_ROTATED}"
    local current_jwt_key="${JWT_SECRET_KEY}"
    local current_auth_secret="${AUTH_SECRET}"

    local needs_generation=false
    local needs_rotation=false

    # Check if SECRET_KEY is missing, is placeholder, or too short
    if [ -z "$current_key" ] || [ "$current_key" = "changeme_generate_strong_key_for_production" ] || [ ${#current_key} -lt 32 ] || [[ "$current_key" == *"changeme"* ]] || [[ "$current_key" == *"placeholder"* ]]; then
        needs_generation=true
    fi

    # Check if JWT_SECRET_KEY is missing or is placeholder
    local gen_jwt=false
    if [ -z "$current_jwt_key" ] || [ "$current_jwt_key" = "your_super_secret_jwt_key" ] || [[ "$current_jwt_key" == *"changeme"* ]] || [[ "$current_jwt_key" == *"placeholder"* ]]; then
        gen_jwt=true
    fi

    # Check if AUTH_SECRET is missing or is placeholder
    local gen_auth=false
    if [ -z "$current_auth_secret" ] || [ "$current_auth_secret" = "your_super_secret_auth_key" ] || [[ "$current_auth_secret" == *"changeme"* ]] || [[ "$current_auth_secret" == *"placeholder"* ]]; then
        gen_auth=true
    fi

    # Rotation check
    if [ "$needs_generation" = false ]; then
        if [ "$ROTATE_FORCE" = true ]; then
            echo "🔄 Forced rotation requested. Rotating SECRET_KEY..."
            needs_rotation=true
        elif [ "$CLEAN" = true ]; then
            echo "🧹 Clean start requested. Rotating SECRET_KEY..."
            needs_rotation=true
        elif [ -n "$last_rotated" ]; then
            local now
            now=$(date +%s)
            local age=$((now - last_rotated))
            # Rotate if older than 30 days (2592000 seconds)
            if [ "$age" -gt 2592000 ]; then
                echo "⏰ SECRET_KEY is older than 30 days. Rotating SECRET_KEY..."
                needs_rotation=true
            fi
        else
            # No rotation metadata, set it to current timestamp to start tracking
            local _sc_ts
            _sc_ts=$(date +%s)
            update_env_var "$target_file" "SECRET_KEY_LAST_ROTATED" "$_sc_ts"
            export SECRET_KEY_LAST_ROTATED="$_sc_ts"
        fi
    fi

    # Generate or rotate SECRET_KEY
    if [ "$needs_generation" = true ] || [ "$needs_rotation" = true ]; then
        local new_key=""
        if command -v python3 &>/dev/null; then
            new_key=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null)
        fi
        if [ -z "$new_key" ] && command -v openssl &>/dev/null; then
            new_key=$(openssl rand -hex 32 2>/dev/null)
        fi
        if [ -z "$new_key" ]; then
            new_key=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
        fi

        update_env_var "$target_file" "SECRET_KEY" "$new_key"
        update_env_var "$target_file" "SECRET_KEY_LAST_ROTATED" "$(date +%s)"
        
        export SECRET_KEY="$new_key"
        local _sc_ts
        _sc_ts=$(date +%s)
        export SECRET_KEY_LAST_ROTATED="$_sc_ts"
        echo "✅ Generated and set new SECRET_KEY in $target_file"
    fi

    # Generate or rotate JWT_SECRET_KEY
    if [ "$gen_jwt" = true ] || [ "$needs_rotation" = true ]; then
        local new_jwt_key=""
        if command -v python3 &>/dev/null; then
            new_jwt_key=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null)
        fi
        if [ -z "$new_jwt_key" ] && command -v openssl &>/dev/null; then
            new_jwt_key=$(openssl rand -hex 32 2>/dev/null)
        fi
        if [ -z "$new_jwt_key" ]; then
            new_jwt_key=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
        fi
        update_env_var "$target_file" "JWT_SECRET_KEY" "$new_jwt_key"
        export JWT_SECRET_KEY="$new_jwt_key"
        echo "✅ Generated and set new JWT_SECRET_KEY in $target_file"
    fi

    # Generate or rotate AUTH_SECRET
    if [ "$gen_auth" = true ] || [ "$needs_rotation" = true ]; then
        local new_auth_secret=""
        if command -v python3 &>/dev/null; then
            new_auth_secret=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null)
        fi
        if [ -z "$new_auth_secret" ] && command -v openssl &>/dev/null; then
            new_auth_secret=$(openssl rand -base64 32 2>/dev/null | tr -d '+/=')
        fi
        if [ -z "$new_auth_secret" ]; then
            new_auth_secret=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
        fi
        update_env_var "$target_file" "AUTH_SECRET" "$new_auth_secret"
        export AUTH_SECRET="$new_auth_secret"
        echo "✅ Generated and set new AUTH_SECRET in $target_file"
    fi
}

# 1. Load Environment Variables
if [ -f ".env" ]; then
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
fi

# Load mode-specific overrides
ENV_FILE=".env.$MODE"
if [ -f "$ENV_FILE" ]; then
    echo "⚡ Loading overrides from $ENV_FILE"
    set -o allexport
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +o allexport
elif [ "$MODE" != "dev" ] && [ "$MODE" != "prod" ]; then
    echo "⚠️ Warning: Mode '$MODE' requested but $ENV_FILE not found. Falling back to base .env."
fi

# Auto-generate or rotate keys in all modes
auto_generate_or_rotate_keys

# 1a. Validate required environment variables
REQUIRED_VARS=("DATABASE_URL" "REDIS_URL" "SECRET_KEY")
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables: ${MISSING_VARS[*]}"
    exit 1
fi

# Warning for production-critical variables
if [ "$MODE" != "dev" ] && [ -z "$AUTH_SECRET" ]; then
    echo "❌ Error: AUTH_SECRET is required for '$MODE' mode but is not set."
    exit 1
elif [ -z "$AUTH_SECRET" ]; then
    echo "⚠️  Warning: AUTH_SECRET is not set. Auth might fail in $MODE mode."
fi

# 2. Version and Metadata
# Robustly extract version from pyproject.toml even on older python environments
VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null \
    || python3 -c "import re; print(re.search(r'version\s*=\s*\"([^\"]+)\"', open('pyproject.toml').read()).group(1))" 2>/dev/null \
    || grep -m 1 "version =" pyproject.toml | cut -d '"' -f 2 \
    || echo "0.0.0")

if [ -n "$CUSTOM_VERSION" ]; then
    export APP_VERSION="$CUSTOM_VERSION"
else
    if [ "$MODE" == "dev" ]; then
        export APP_VERSION="${VERSION}.dev"
    else
        export APP_VERSION="${VERSION}"
    fi
fi
# 2b. Helper to terminate process from pidfile
terminate_from_pidfile() {
    pidfile="$1"
    desc="$2"

    if [ ! -f "${pidfile}" ]; then
        return 0
    fi

    pid="$(cat "${pidfile}" 2>/dev/null || true)"
    if [ -z "${pid}" ]; then
        rm -f "${pidfile}"
        return 0
    fi

    if ! kill -0 "${pid}" 2>/dev/null; then
        # Process is already gone; clean up stale pidfile.
        rm -f "${pidfile}"
        return 0
    fi

    echo "🧹 Terminating ${desc} (PID ${pid})..."
    # First try graceful shutdown (SIGTERM).
    kill "${pid}" 2>/dev/null || true

    # Wait up to 5 seconds for the process to exit.
    for _ in 1 2 3 4 5; do
        if ! kill -0 "${pid}" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    # If still running, escalate to SIGKILL.
    if kill -0 "${pid}" 2>/dev/null; then
        echo "⚠️  ${desc} did not exit gracefully; sending SIGKILL..."
        kill -9 "${pid}" 2>/dev/null || true
    fi

    rm -f "${pidfile}"
}

# 3. Stop Command Dispatch
PID_DIR=".pids"

if [ "$STOP" = true ]; then
    echo "🛑 Stopping iqoqo in '$MODE' mode..."
    if [ "$MODE" == "dev" ]; then
        # Kill local processes if they exist
        terminate_from_pidfile "$PID_DIR/flask.pid" "Flask API server"
        terminate_from_pidfile "$PID_DIR/celery.pid" "Celery worker"
        terminate_from_pidfile "$PID_DIR/next.pid" "Next.js dev server"
        rm -rf "$PID_DIR"
        docker compose down
        if [ -f "docker-compose.monitoring.yml" ]; then
            echo "📊 Stopping local monitoring stack..."
            docker compose -f docker-compose.monitoring.yml down || true
        fi
    else
        export COMPOSE_PROJECT_NAME="iqoqo-$MODE"
        [ "$MODE" == "prod" ] && export COMPOSE_PROJECT_NAME="iqoqo"
        COMPOSE_DOWN_CMD="docker compose -f docker-compose.yml"
        $COMPOSE_DOWN_CMD down --remove-orphans
    fi
    echo "✅ Stopped."
    exit 0
fi

# Activate/Bootstrap Virtual Environment
if [ ! -d ".venv" ]; then
    echo "🔧 Bootstrapping virtual environment..."
    python3 -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -r requirements.txt
    if [ "$OTEL_TRACES_EXPORTER" = "otlp" ] && command -v opentelemetry-bootstrap &>/dev/null; then
        opentelemetry-bootstrap -a install
    fi
    touch .venv/bin/activate
elif [ "requirements.txt" -nt ".venv/bin/activate" ]; then
    echo "🔧 Syncing virtual environment with requirements.txt..."
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -r requirements.txt
    if [ "$OTEL_TRACES_EXPORTER" = "otlp" ] && command -v opentelemetry-bootstrap &>/dev/null; then
        opentelemetry-bootstrap -a install
    fi
    touch .venv/bin/activate
else
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

if [ "$MODE" == "dev" ]; then
    # --- LOCAL DEV MODE ---

    # Load Tunnel Configuration if requested
    if [ "$TUNNEL" = true ] && [ -f ".env.dev" ]; then
        echo "⚡ Loading Tunnel Configuration (.env.dev)"
        set -o allexport
        # shellcheck disable=SC1091
        source .env.dev
        set +o allexport
    elif [ "$TUNNEL" = false ]; then
        export NEXTAUTH_URL="http://localhost:3000"
        export AUTH_TRUST_HOST="false"
        # Ensure URLs point to localhost for host-side processes
        export DATABASE_URL="${DATABASE_URL/@db:/@localhost:}"
        export REDIS_URL="redis://localhost:6379/0"
    fi

    if [ "$VALIDATE_ONLY" = true ]; then
        echo "✅ Configuration validation successful (dev)."
        exit 0
    fi

    # Start DB/Redis in Docker (slim mode)
    echo "🔧 Checking background services (db, redis)..."
    if ! COMPOSE_ERR=$(docker compose up -d db redis 2>&1); then
        if docker info &>/dev/null; then
            echo "❌ Error: Docker is running but 'docker compose up' failed."
            echo "Details:"
            echo "$COMPOSE_ERR"
            exit 1
        fi

        echo "Docker command failed. Checking for Colima..."
        if command -v colima &> /dev/null; then
            if colima status &> /dev/null; then
                echo "Colima is running but Docker failed. Restarting Colima..."
                colima stop
            fi
            echo "Starting Colima with DNS fix..."
            if ! colima start --dns 8.8.8.8; then
                echo "Colima start failed. Attempting to force stop and restart..."
                colima stop --force
                if ! colima start --dns 8.8.8.8; then
                    echo "Error: Failed to start Colima."
                    if [ -t 0 ]; then
                        printf "Do you want to reset Colima (delete and restart)? This will delete all Docker data! [y/N] "
                        read -n 1 -r REPLY
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            colima delete --force
                            if ! colima start --dns 8.8.8.8; then
                                echo "Error: Still failed to start Colima."
                                exit 1
                            fi
                        else
                            exit 1
                        fi
                    else
                        echo "Hint: Try running 'colima delete' and then 'colima start' in a terminal to reset the VM."
                        exit 1
                    fi
                fi
            fi
            docker compose up -d db redis || exit 1
        else
            echo "Error: Docker is not running. Please start Docker."
            echo "Details:"
            echo "$COMPOSE_ERR"
            exit 1
        fi
    fi

    # Start Monitoring Stack if OTel is enabled and compose file exists
    if [ "$OTEL_TRACES_EXPORTER" = "otlp" ] && [ -f "docker-compose.monitoring.yml" ]; then
        echo "📊 OpenTelemetry tracing is enabled. Ensuring local OpenObserve monitoring stack is running..."
        docker network create iqoqo_default 2>/dev/null || true
        # Clean up any conflicting container names to prevent startup failure
        docker rm -f \
            "${COMPOSE_PROJECT_NAME:-iqoqo}-openobserve" \
            "${COMPOSE_PROJECT_NAME:-iqoqo}-otel-collector" \
            iqoqo-openobserve \
            iqoqo-otel-collector 2>/dev/null || true
        docker compose -f docker-compose.monitoring.yml up -d || true

        # Wait for OpenObserve readiness and fetch the dynamic RUM client token
        echo "📊 Waiting for OpenObserve to be ready..."
        auth_header="Basic YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ="
        if [ -n "$OPENOBSERVE_ROOT_USER" ] && [ -n "$OPENOBSERVE_ROOT_PASSWORD" ]; then
            encoded=$(python3 -c "import base64; print(base64.b64encode(b'${OPENOBSERVE_ROOT_USER}:${OPENOBSERVE_ROOT_PASSWORD}').decode('utf-8'))" 2>/dev/null)
            if [ -n "$encoded" ]; then
                auth_header="Basic $encoded"
            fi
        fi

        for i in {1..30}; do
            token_response=$(curl -s -H "Authorization: $auth_header" http://localhost:5080/api/default/rumtoken 2>/dev/null)
            if echo "$token_response" | grep -q "rum_token"; then
                fetched_token=$(echo "$token_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['rum_token'])" 2>/dev/null)
                if [ -n "$fetched_token" ]; then
                    echo "📊 Successfully fetched active OpenObserve RUM token: $fetched_token"
                    export OPENOBSERVE_RUM_CLIENT_TOKEN="$fetched_token"
                    # Keep local configuration files updated
                    update_env_var ".env" "OPENOBSERVE_RUM_CLIENT_TOKEN" "$fetched_token"
                    if [ -f ".env.dev" ]; then
                        update_env_var ".env.dev" "OPENOBSERVE_RUM_CLIENT_TOKEN" "$fetched_token"
                    fi
                    break
                fi
            fi
            sleep 1
        done
    fi

    # Wait for DB readiness
    for i in {1..15}; do
        if docker compose exec -T db pg_isready -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" &>/dev/null; then
            break
        fi
        sleep 1
    done

    # PID Management & Cleanup
    PID_DIR=".pids"
    mkdir -p "$PID_DIR"

    # terminate_from_pidfile is defined globally above

    echo "🧹 Cleaning up previous dev processes..."
    terminate_from_pidfile "$PID_DIR/flask.pid" "Flask API server"
    terminate_from_pidfile "$PID_DIR/celery.pid" "Celery worker"
    terminate_from_pidfile "$PID_DIR/next.pid" "Next.js dev server"

    # Legacy cleanups
    terminate_from_pidfile ".flask.pid" "Legacy Flask"
    terminate_from_pidfile ".frontend.pid" "Legacy Frontend"
    terminate_from_pidfile ".celery.pid" "Legacy Celery"
    terminate_from_pidfile "$PID_DIR/web_server.pid" "Legacy Flask (New naming)"
    terminate_from_pidfile "$PID_DIR/celery_worker.pid" "Legacy Celery (New naming)"
    terminate_from_pidfile "$PID_DIR/next_dev.pid" "Legacy Next.js (New naming)"

    # Ensure ports are free (aggressive cleanup for common ports)
    for port in "$WEB_PORT" 3000; do
        port_pid=$(lsof -t -i:"$port" 2>/dev/null)
        if [ -n "$port_pid" ]; then
            echo "⚠️  Port $port still occupied by PID $port_pid. Killing..."
            kill -9 "$port_pid" 2>/dev/null
        fi
    done

    # Next.js Stale Lock Detection
    for LOCK in "frontend/.next/lock" "frontend/.next/dev/lock"; do
        if [ -f "$LOCK" ]; then
            echo "⚠️  Stale Next.js lock file detected: $LOCK"
            if [ -t 0 ]; then
                printf "Do you want to fix this (kill zombie processes and clear cache)? [y/N] "
                read -n 1 -r REPLY
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    ZOMBIE_PIDS=$(lsof -t -i :3000 2>/dev/null || true)
                    if [ -n "$ZOMBIE_PIDS" ]; then
                        echo "⚠️  Killing zombie process(es) on port 3000 (PIDs: $ZOMBIE_PIDS)..."
                        kill -9 "$ZOMBIE_PIDS" 2>/dev/null || true
                    fi
                    echo "🧹 Clearing corrupted Next.js cache..."
                    rm -rf "frontend/.next"
                    echo "✅ Cleanup complete."
                else
                    echo "❌ Exiting. Please remove the lock file manually."
                    exit 1
                fi
            else
                 echo "❌ Lock file exists and script is non-interactive. Please remove $LOCK manually."
                 exit 1
            fi
        fi
    done

    # Termination Helper
    cleanup() {
        echo -e "\n🛑 Stopping servers..."
        terminate_from_pidfile "$PID_DIR/flask.pid" "Flask API server"
        terminate_from_pidfile "$PID_DIR/celery.pid" "Celery worker"
        terminate_from_pidfile "$PID_DIR/next.pid" "Next.js dev server"
        rm -rf "$PID_DIR"
        exit 0
    }
    trap cleanup INT TERM

    # 4. Install frontend dependencies if needed
    if [ -d "frontend" ] && [ ! -d "frontend/node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        (cd frontend && npm install)
    fi

    # 4a. Setup DB role and run migrations
    [ -f "scripts/setup_db.sh" ] && bash scripts/setup_db.sh
    python scripts/fix_alembic.py
    flask db upgrade

    # 5. Run Flask API (background) + Next.js frontend
    export FLASK_APP=run.py
    export FLASK_DEBUG=1
    WEB_PORT=${WEB_PORT:-5000}
    if [ "$OTEL_TRACES_EXPORTER" = "otlp" ]; then
        echo "📡 Starting Flask API with OpenTelemetry auto-instrumentation (traces + metrics + logs)..."
        OTEL_SERVICE_NAME="iqoqo-api" \
        OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-otlp}" \
        OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-otlp}" \
        OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED="${OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED:-true}" \
        opentelemetry-instrument flask run --port "$WEB_PORT" &
    else
        flask run --port "$WEB_PORT" &
    fi
    echo $! > "$PID_DIR/flask.pid"

    # Start Celery
    CELERY_POOL="prefork"
    if [ "$(uname)" = "Darwin" ]; then
        CELERY_POOL="threads"
    fi

    if [ "$OTEL_TRACES_EXPORTER" = "otlp" ]; then
        echo "📡 Starting Celery worker with OpenTelemetry auto-instrumentation (traces + metrics + logs)..."
        OTEL_SERVICE_NAME="iqoqo-celery-worker" \
        OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-otlp}" \
        OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-otlp}" \
        OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED="${OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED:-true}" \
        opentelemetry-instrument celery -A app.core.celery_app:celery worker --pool="$CELERY_POOL" --loglevel=info &
    else
        .venv/bin/celery -A app.core.celery_app:celery worker --pool="$CELERY_POOL" --loglevel=info &
    fi
    echo $! > "$PID_DIR/celery.pid"

    # Start Next.js
    if [ -d "frontend" ]; then
        (cd frontend && \
         NEXT_PUBLIC_API_URL="/api" \
         FLASK_API_URL="http://127.0.0.1:${WEB_PORT}/api" \
         NEXT_PUBLIC_FRONTEND_URL="${NEXT_PUBLIC_FRONTEND_URL}" \
         NEXTAUTH_URL="${NEXTAUTH_URL}" \
         AUTH_URL="${AUTH_URL}" \
         AUTH_TRUST_HOST="${AUTH_TRUST_HOST}" \
         NEXT_PUBLIC_APP_VERSION="${APP_VERSION}" \
         OTEL_SERVICE_NAME="iqoqo-frontend" \
         OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT}" \
         OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN="${OPENOBSERVE_RUM_CLIENT_TOKEN:-rumST8CMTyDstlTbPUm}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_SITE="${OPENOBSERVE_RUM_SITE:-localhost:5080}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_ENV="${OPENOBSERVE_RUM_ENV:-development}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_ORG_ID="${OPENOBSERVE_RUM_ORG_ID:-default}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP="${OPENOBSERVE_RUM_INSECURE_HTTP:-true}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_API_VERSION="${OPENOBSERVE_RUM_API_VERSION:-v1}" \
         NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL="${OPENOBSERVE_RUM_PRIVACY_LEVEL:-allow}" \
         npm run dev) &
         echo $! > "$PID_DIR/next.pid"
    fi


    echo ""
    echo "════════════════════════════════════════════════"
    echo "  iqoqo v${APP_VERSION} (${MODE}) servers running"
    echo "  Flask API  → http://127.0.0.1:${WEB_PORT}"
    if [ "$TUNNEL" = true ]; then
        echo "  Public URL → https://dev.iqoqo.cc"
    else
        echo "  Local URL  → http://localhost:3000"
    fi
    echo "  Press Ctrl+C to stop all servers"
    echo "════════════════════════════════════════════════"
    echo ""
    wait

else
    # --- FULL DOCKER MODE ---

    export ENV_FILE="$ENV_FILE" # Injected into compose
    export COMPOSE_PROJECT_NAME="iqoqo-$MODE"
    if [ "$MODE" == "prod" ]; then
        # Maintain volume continuity for 'prod' mode if preferred
        export COMPOSE_PROJECT_NAME="iqoqo"
    fi

    # Ensure URLs point to service names for container-internal networking
    export DATABASE_URL="${DATABASE_URL/@localhost:/@db:}"
    export REDIS_URL="${REDIS_URL/@localhost:/@redis:}"

    if [ "$CLEAN" = true ]; then
        echo "🧹 Cleaning up previous instances for $COMPOSE_PROJECT_NAME..."
        docker compose down --remove-orphans
    fi

    echo "🔧 Checking service readiness..."
    COMPOSE_BASE="docker compose -f docker-compose.yml"
    $COMPOSE_BASE up -d db redis

    # Wait for DB to be ready
    echo "⏳ Waiting for database..."
    DB_READY=false
    # shellcheck disable=SC2034
    for i in {1..30}; do
        if $COMPOSE_BASE exec -T db pg_isready -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" &>/dev/null; then
            echo "✅ Database is ready"
            DB_READY=true
            break
        fi
        sleep 1
    done
    if [ "$DB_READY" = false ]; then
        echo "❌ Database failed to become ready after 30 seconds"
        exit 1
    fi

    # Pre-flight migration checks
    MIGRATION_ROWS=$($COMPOSE_BASE exec -T db psql -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" -At -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "")
    MIGRATION_COUNT=$(echo "$MIGRATION_ROWS" | grep -c '[^[:space:]]' || true)

    if [ "$MIGRATION_COUNT" -gt 1 ]; then
        echo "⚠️  WARNING: Multiple Alembic heads detected in the database:"
        # shellcheck disable=SC2001
        echo "$MIGRATION_ROWS" | sed 's/^/   /'
        CURRENT_MIGRATION=""
    elif [ "$MIGRATION_COUNT" -eq 1 ]; then
        CURRENT_MIGRATION=$(echo "$MIGRATION_ROWS" | tr -d '[:space:]')
    else
        CURRENT_MIGRATION=""
    fi

    # Get expected Alembic heads from source code (most reliable method)
    EXPECTED_HEADS=$(python3 -c "
try:
    from alembic.script import ScriptDirectory
    heads = ScriptDirectory('migrations').get_heads()
    print(' '.join(heads))
except Exception:
    print('')
" 2>/dev/null || echo "")
    HEAD_COUNT=$(echo "$EXPECTED_HEADS" | wc -w | tr -d ' ')

    if [ "$HEAD_COUNT" -eq 1 ]; then
        EXPECTED_VERSION="$EXPECTED_HEADS"
    elif [ "$HEAD_COUNT" -gt 1 ]; then
        echo "⚠️  WARNING: Multiple Alembic heads in source scripts: $EXPECTED_HEADS"
        EXPECTED_VERSION=""
    else
        EXPECTED_VERSION=""
    fi

    if [ -n "$CURRENT_MIGRATION" ] && [ -n "$EXPECTED_VERSION" ]; then
        if [ "$CURRENT_MIGRATION" != "$EXPECTED_VERSION" ]; then
            echo "⚠️  Migration mismatch! DB: $CURRENT_MIGRATION → Expected: $EXPECTED_VERSION. Upgrading..."
        else
            echo "✅ Migration state: $CURRENT_MIGRATION"
        fi
    else
        echo "ℹ️  Could not determine migration state (current: '${CURRENT_MIGRATION:-none}', expected: '${EXPECTED_VERSION:-unknown}')"
    fi

    # Backup logic
    if [ "$BACKUP" = true ]; then
        BACKUP_FILE="exports/backup_${MODE}_$(date +%Y%m%d_%H%M%S).sql"
        echo "📦 Creating backup: $BACKUP_FILE"
        mkdir -p exports
        $COMPOSE_BASE exec -T db pg_dump -U "${POSTGRES_USER:-iqoqo}" "${POSTGRES_DB:-iqoqo}" > "$BACKUP_FILE" || echo "⚠️  Backup failed!"
    fi

    COMPOSE_CMD="docker compose -f docker-compose.yml"
    if [ -f "docker-compose.monitoring.yml" ]; then
        echo "📊 Found docker-compose.monitoring.yml, starting with OpenObserve monitoring..."
        COMPOSE_CMD="$COMPOSE_CMD -f docker-compose.monitoring.yml"
    fi

    if [ "$VALIDATE_ONLY" = true ]; then
        echo "✅ Configuration validation successful (prod)."
        exit 0
    fi

    if [ "$PREBUILT" = true ]; then
        echo "📦 Using pre-built images from ghcr.io..."
        COMPOSE_CMD="$COMPOSE_CMD -f docker-compose.prebuilt.yml"
        if ! $COMPOSE_CMD pull; then
            echo "❌ Error: Failed to pull pre-built images."
            if command -v gh &>/dev/null; then
                if [ -t 0 ]; then
                    printf "🤔 Do you want to attempt automatic login via GitHub CLI (gh)? [y/N] "
                    read -n 1 -r REPLY
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        echo "🔑 Attempting GHCR login..."
                        if gh auth token | docker login ghcr.io -u "${GITHUB_USER:-sebastiankruk}" --password-stdin; then
                             echo "✅ Login successful! Retrying pull..."
                             $COMPOSE_CMD pull || { echo "❌ Still failed to pull. Please check permissions."; exit 1; }
                        else
                             echo "❌ Automatic login failed. Please run 'docker login ghcr.io' manually."
                             exit 1
                        fi
                    else
                        exit 1
                    fi
                else
                    echo "💡 Hint: Try 'gh auth token | docker login ghcr.io -u YOUR_USER --password-stdin' or run without --prebuilt."
                    exit 1
                fi
            else
                echo "❌ Please log in to ghcr.io manually (docker login ghcr.io) or run without --prebuilt."
                exit 1
            fi
        fi
        BUILD_FLAG=""
    else
        echo "🔨 Building images locally from source..."
        BUILD_FLAG="--build"
    fi

    # Ensure .allegro_token.json is a regular file.
    # Docker creates missing bind-mount source paths as directories,
    # which breaks container restarts for file-target mounts.
    if [ ! -f ".allegro_token.json" ]; then
        rm -rf ".allegro_token.json"
        printf '{}\n' > ".allegro_token.json"
    fi

    echo "🚀 Starting full stack for $COMPOSE_PROJECT_NAME (v$APP_VERSION)..."
    if ! $COMPOSE_CMD up -d $BUILD_FLAG --remove-orphans; then
        echo "❌ Error: Failed to start full stack for $COMPOSE_PROJECT_NAME."
        exit 1
    fi

    # Wait for services to settle
    echo "⏳ Waiting 10 seconds for services to settle..."
    sleep 10

    # Get status of all containers
    SERVICES_STATUS=$($COMPOSE_CMD ps --format "{{.Service}}: {{.State}} ({{.Health}})")

    echo "📊 Service Status:"
    # shellcheck disable=SC2001
    echo "$SERVICES_STATUS" | sed 's/^/  /'

    # Detect any crashed or unhealthy services
    BAD_SERVICES=$(echo "$SERVICES_STATUS" | grep -E "exited|dead|unhealthy" || true)

    if [ -n "$BAD_SERVICES" ]; then
        echo "❌ Error: Some services failed to start or are unhealthy!"
        echo "$BAD_SERVICES" | cut -d':' -f1 | while read -r service; do
            if [ -n "$service" ]; then
                echo "════════════════════════════════════════════════"
                echo "  Dumping logs for failed service: $service"
                echo "════════════════════════════════════════════════"
                $COMPOSE_CMD logs --tail 50 "$service"
            fi
        done
        exit 1
    fi

    echo "✅ Success! Deployment ready."
    if [ "$MODE" != "prod" ]; then
        echo "🌐 URL: http://localhost:${NGINX_PORT:-8000}"
    fi
fi
