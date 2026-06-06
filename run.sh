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
# Usage: ./run.sh [mode] [--clean] [--backup] [--tunnel]
#
# Modes:
#   dev      (default) Run Flask, Celery, and Next.js as local processes.
#            Only db and redis are started in Docker.
#   ANYTHING else uses full Docker Compose (e.g., prod, preview).
#
# Options:
#   --clean  Stop and remove previous instances/containers.
#   --backup Create a pre-deployment database backup (Docker modes only).
#   --tunnel Load dev.iqoqo.cc configuration (dev mode only).

# 0. Set Mode and Parameters
MODE="dev"
MODE_SET=false
EXTRA_ARGS=()
TUNNEL=false
CLEAN=false
BACKUP=false
PREBUILT=false
STOP=false
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
cd "$(dirname "$0")"

# 1. Load Environment Variables
if [ -f ".env" ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Load mode-specific overrides
ENV_FILE=".env.$MODE"
if [ -f "$ENV_FILE" ]; then
    echo "⚡ Loading overrides from $ENV_FILE"
    set -o allexport
    source "$ENV_FILE"
    set +o allexport
elif [ "$MODE" != "dev" ] && [ "$MODE" != "prod" ]; then
    echo "⚠️ Warning: Mode '$MODE' requested but $ENV_FILE not found. Falling back to base .env."
fi

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

# Activate/Bootstrap Virtual Environment
if [ ! -d ".venv" ]; then
    echo "🔧 Bootstrapping virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    touch .venv/bin/activate
elif [ "requirements.txt" -nt ".venv/bin/activate" ]; then
    echo "🔧 Syncing virtual environment with requirements.txt..."
    source .venv/bin/activate
    pip install -r requirements.txt
    touch .venv/bin/activate
else
    source .venv/bin/activate
fi

# 3. Execution Dispatch
PID_DIR=".pids"

if [ "$STOP" = true ]; then
    echo "🛑 Stopping iqoqo in '$MODE' mode..."
    if [ "$MODE" == "dev" ]; then
        # Kill local processes if they exist
        [ -f "$PID_DIR/flask.pid" ] && kill $(cat "$PID_DIR/flask.pid") 2>/dev/null || true
        [ -f "$PID_DIR/celery.pid" ] && kill $(cat "$PID_DIR/celery.pid") 2>/dev/null || true
        [ -f "$PID_DIR/next.pid" ] && kill $(cat "$PID_DIR/next.pid") 2>/dev/null || true
        rm -rf "$PID_DIR"
        docker compose down
    else
        export COMPOSE_PROJECT_NAME="iqoqo-$MODE"
        [ "$MODE" == "prod" ] && export COMPOSE_PROJECT_NAME="iqoqo"
        docker compose down --remove-orphans
    fi
    echo "✅ Stopped."
    exit 0
fi

if [ "$MODE" == "dev" ]; then
    # --- LOCAL DEV MODE ---

    # Load Tunnel Configuration if requested
    if [ "$TUNNEL" = true ] && [ -f ".env.dev" ]; then
        echo "⚡ Loading Tunnel Configuration (.env.dev)"
        set -o allexport
        source .env.dev
        set +o allexport
    elif [ "$TUNNEL" = false ]; then
        export NEXTAUTH_URL="http://localhost:3000"
        export AUTH_TRUST_HOST="false"
        # Ensure URLs point to localhost for host-side processes
        export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/@db:/@localhost:/')
        export REDIS_URL="redis://localhost:6379/0"
    fi

    # Start DB/Redis in Docker (slim mode)
    echo "🔧 Checking background services (db, redis)..."
    if ! docker compose up -d db redis &>/dev/null; then
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
                        read -p "Do you want to reset Colima (delete and restart)? This will delete all Docker data! [y/N] " -n 1 -r
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
            exit 1
        fi
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
                read -p "Do you want to fix this (kill zombie processes and clear cache)? [y/N] " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    ZOMBIE_PIDS=$(lsof -t -i :3000 2>/dev/null || true)
                    if [ -n "$ZOMBIE_PIDS" ]; then
                        echo "⚠️  Killing zombie process(es) on port 3000 (PIDs: $ZOMBIE_PIDS)..."
                        kill -9 $ZOMBIE_PIDS 2>/dev/null || true
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
        [ -f "$PID_DIR/flask.pid" ] && kill $(cat "$PID_DIR/flask.pid") 2>/dev/null || true
        [ -f "$PID_DIR/celery.pid" ] && kill $(cat "$PID_DIR/celery.pid") 2>/dev/null || true
        [ -f "$PID_DIR/next.pid" ] && kill $(cat "$PID_DIR/next.pid") 2>/dev/null || true
        rm -rf "$PID_DIR"
        sleep 1
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
    flask run --port "$WEB_PORT" &
    echo $! > "$PID_DIR/flask.pid"

    # Start Celery
    .venv/bin/celery -A app.core.celery_app:celery worker --loglevel=info &
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
    export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/@localhost:/@db:/')
    export REDIS_URL=$(echo "$REDIS_URL" | sed 's/@localhost:/@redis:/')

    if [ "$CLEAN" = true ]; then
        echo "🧹 Cleaning up previous instances for $COMPOSE_PROJECT_NAME..."
        docker compose down --remove-orphans
    fi

    echo "🔧 Checking service readiness..."
    docker compose up -d db redis

    # Wait for DB to be ready
    echo "⏳ Waiting for database..."
    DB_READY=false
    for i in {1..30}; do
        if docker compose exec -T db pg_isready -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" &>/dev/null; then
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
    MIGRATION_ROWS=$(docker compose exec -T db psql -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" -At -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "")
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
        docker compose exec -T db pg_dump -U "${POSTGRES_USER:-iqoqo}" "${POSTGRES_DB:-iqoqo}" > "$BACKUP_FILE" || echo "⚠️  Backup failed!"
    fi

    COMPOSE_CMD="docker compose -f docker-compose.yml"

    if [ "$PREBUILT" = true ]; then
        echo "📦 Using pre-built images from ghcr.io..."
        COMPOSE_CMD="$COMPOSE_CMD -f docker-compose.prebuilt.yml"
        if ! $COMPOSE_CMD pull; then
            echo "❌ Error: Failed to pull pre-built images."
            if command -v gh &>/dev/null; then
                if [ -t 0 ]; then
                    read -p "🤔 Do you want to attempt automatic login via GitHub CLI (gh)? [y/N] " -n 1 -r
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
    [ "$MODE" != "prod" ] && echo "🌐 URL: http://localhost:${NGINX_PORT:-8000}"
fi
