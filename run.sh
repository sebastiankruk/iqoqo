#!/bin/bash
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

set -e

# 0. Set Mode and Parameters
MODE="dev"
EXTRA_ARGS=()
TUNNEL=false
CLEAN=false
BACKUP=false

# Simple argument parsing
for arg in "$@"; do
    case $arg in
        dev|preview|prod)
            MODE=$arg
            shift
            ;;
        --tunnel)
            TUNNEL=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --backup)
            BACKUP=true
            shift
            ;;
        *)
            # Non-flag positional arg (if first) is treated as mode
            if [[ "$arg" != -* ]] && [[ -z "$MODE_SET" ]]; then
                MODE=$arg
                MODE_SET=true
            else
                EXTRA_ARGS+=("$arg")
            fi
            ;;
    esac
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
if [ -z "$AUTH_SECRET" ]; then
    echo "⚠️  Warning: AUTH_SECRET is not set. Auth might fail in $MODE mode."
fi

# 2. Version and Metadata
VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb')).get('project', {}).get('version'))" 2>/dev/null || echo "0.0.0")
if [ "$MODE" == "dev" ]; then
    export APP_VERSION="${VERSION}.dev"
else
    export APP_VERSION="${VERSION}"
fi

# Activate/Bootstrap Virtual Environment
if [ ! -d ".venv" ]; then
    echo "🔧 Bootstrapping virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 3. Execution Dispatch
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
    fi

    # Start DB/Redis in Docker (slim mode)
    echo "🔧 Starting background services (db, redis)..."
    docker compose up -d db redis

    # Wait for DB readiness
    for i in {1..15}; do
        if docker compose exec -T db pg_isready -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" &>/dev/null; then
            break
        fi
        sleep 1
    done

    # PID Management
    PID_DIR=".pids"
    mkdir -p "$PID_DIR"

    # Termination Helper
    cleanup() {
        echo -e "\n🛑 Stopping servers..."
        [ -f "$PID_DIR/flask.pid" ] && kill $(cat "$PID_DIR/flask.pid") 2>/dev/null || true
        [ -f "$PID_DIR/celery.pid" ] && kill $(cat "$PID_DIR/celery.pid") 2>/dev/null || true
        [ -f "$PID_DIR/next.pid" ] && kill $(cat "$PID_DIR/next.pid") 2>/dev/null || true
        rm -rf "$PID_DIR"
        exit 0
    }
    trap cleanup INT TERM

    # Setup DB role and run migrations
    [ -f "scripts/setup_db.sh" ] && bash scripts/setup_db.sh
    python scripts/fix_alembic.py
    flask db upgrade

    # Start Flask API
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
         NEXT_PUBLIC_APP_VERSION="${APP_VERSION}" \
         npm run dev) &
        echo $! > "$PID_DIR/next.pid"
    fi

    echo "✅ Dev servers running (API: $WEB_PORT, Next: 3000)"
    wait

else
    # --- FULL DOCKER MODE ---
    
    export ENV_FILE="$ENV_FILE" # Injected into compose
    export COMPOSE_PROJECT_NAME="iqoqo-$MODE"
    if [ "$MODE" == "prod" ]; then
        # Maintain volume continuity for 'prod' mode if preferred
        export COMPOSE_PROJECT_NAME="iqoqo"
    fi

    if [ "$CLEAN" = true ]; then
        echo "🧹 Cleaning up previous instances for $COMPOSE_PROJECT_NAME..."
        docker compose down --remove-orphans
    fi

    echo "🔧 Checking service readiness..."
    docker compose up -d db redis

    # Wait for DB to be ready
    echo "⏳ Waiting for database..."
    for i in {1..30}; do
        if docker compose exec -T db pg_isready -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" &>/dev/null; then
            break
        fi
        sleep 1
    done

    # Pre-flight migration checks
    MIGRATION_ROWS=$(docker compose exec -T db psql -U "${POSTGRES_USER:-iqoqo}" -d "${POSTGRES_DB:-iqoqo}" -At -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "")
    MIGRATION_COUNT=$(echo "$MIGRATION_ROWS" | grep -c '[^[:space:]]' || true)
    
    EXPECTED_VERSION=$(python3 -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
try:
    config = Config('migrations/alembic.ini')
    heads = ScriptDirectory.from_config(config).get_heads()
    print(heads[0] if heads else '')
except Exception:
    print('')
" 2>/dev/null || echo "")

    if [ -n "$MIGRATION_ROWS" ] && [ "$MIGRATION_COUNT" -eq 1 ]; then
        CURRENT=$(echo "$MIGRATION_ROWS" | tr -d '[:space:]')
        if [ "$CURRENT" != "$EXPECTED_VERSION" ]; then
            echo "⚠️  Migration mismatch (DB: $CURRENT, Code: $EXPECTED_VERSION). Upgrading..."
        else
            echo "✅ Migration state: $CURRENT"
        fi
    elif [ "$MIGRATION_COUNT" -gt 1 ]; then
        echo "⚠️  Multiple Alembic heads detected!"
    fi

    # Backup logic
    if [ "$BACKUP" = true ]; then
        BACKUP_FILE="exports/backup_${MODE}_$(date +%Y%m%d_%H%M%S).sql"
        echo "📦 Creating backup: $BACKUP_FILE"
        mkdir -p exports
        docker compose exec -T db pg_dump -U "${POSTGRES_USER:-iqoqo}" "${POSTGRES_DB:-iqoqo}" > "$BACKUP_FILE" || echo "⚠️  Backup failed!"
    fi

    echo "🚀 Starting full stack for $COMPOSE_PROJECT_NAME (v$APP_VERSION)..."
    docker compose up -d --build --remove-orphans

    echo "✅ Success! Deployment ready."
    [ "$MODE" != "prod" ] && echo "🌐 URL: http://localhost:${NGINX_PORT:-8000}"
fi
