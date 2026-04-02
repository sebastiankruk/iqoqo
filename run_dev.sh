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

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# 0. Set Mode (Default to dev/tunnel if not specified)
MODE=${MODE:-dev}

VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb')).get('project', {}).get('version'))")
export APP_VERSION="${VERSION:-0}.dev"

# 1. Start Database
echo "Checking database status..."
if command -v docker-compose &> /dev/null; then
    if ! docker-compose up -d db; then
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
            docker-compose up -d db || exit 1
        else
            echo "Error: Docker is not running. Please start Docker."
            exit 1
        fi
    fi
else
    echo "Warning: docker-compose not found. Please ensure your PostgreSQL database is running."
fi

# 1b. Load environment variables
if [ -f ".env" ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Load Tunnel-specific overrides if in dev mode
if [ "$MODE" == "dev" ] && [ -f ".env.dev" ]; then
    echo "⚡ Loading Tunnel Configuration (.env.dev) for dev.iqoqo.cc"
    set -o allexport
    source .env.dev
    set +o allexport
else
    echo "🏠 Running in Localhost mode"
    export NEXTAUTH_URL="http://localhost:3000"
    export AUTH_TRUST_HOST="false"
fi

WEB_PORT=${WEB_PORT:-5000}

# Directory for PID files of processes started by this script
PID_DIR=".pids"

# Create PID directory if it doesn't exist
mkdir -p "${PID_DIR}"

# Gracefully terminate a process referenced by a PID file, with SIGKILL fallback.
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

    echo "  Terminating ${desc} (PID ${pid})..."
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
        echo "  ${desc} did not exit gracefully; sending SIGKILL..."
        kill -9 "${pid}" 2>/dev/null || true
    fi

    rm -f "${pidfile}"
}

# 1c. Kill stale processes and remove lock files to allow clean restart
echo "Cleaning up stale processes and locks..."

# Terminate Flask API process started by this script (if PID file exists)
terminate_from_pidfile "${PID_DIR}/web_server.pid" "Flask API server"

# Terminate Next.js dev server started by this script (if PID file exists)
NEXT_PORT=${NEXT_PORT:-3000}
terminate_from_pidfile "${PID_DIR}/next_dev.pid" "Next.js dev server"

# Remove stale Next.js dev lock file ("Unable to acquire lock" error)
if [ -f "frontend/.next/lock" ]; then
    echo "  Removing stale Next.js lock file..."
    rm -f "frontend/.next/lock"
fi

sleep 1

# 1d. Ensure the database role exists (handles stale Docker volumes)
if [ -f "scripts/setup_db.sh" ]; then
    bash scripts/setup_db.sh
fi

# 2. Activate Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 3. Run database migrations
echo "Running database migrations..."
flask db upgrade
echo "Migrations complete."

# 4. Install frontend dependencies if needed
if [ -d "frontend" ] && [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install)
fi

# 5. Run Flask API (background) + Next.js frontend
export FLASK_APP=run.py
export FLASK_DEBUG=1

echo "Starting Flask API at http://127.0.0.1:${WEB_PORT} ..."
flask run --port "${WEB_PORT}" &
FLASK_PID=$!
echo $FLASK_PID > "${PID_DIR}/web_server.pid"

if [ -d "frontend" ]; then
    echo "Starting Next.js frontend (Mode: $MODE) ..."
    # NEXT_PUBLIC_API_URL="/api" triggers the Next.js config rewrites (proxy)
    # FLASK_API_URL tells the proxy where to send the traffic
    (cd frontend && \
     NEXT_PUBLIC_API_URL="/api" \
     FLASK_API_URL="http://127.0.0.1:${WEB_PORT}/api" \
     NEXT_PUBLIC_FRONTEND_URL="${NEXT_PUBLIC_FRONTEND_URL}" \
     NEXTAUTH_URL="${NEXTAUTH_URL}" \
     AUTH_URL="${AUTH_URL}" \
     AUTH_TRUST_HOST="${AUTH_TRUST_HOST}" \
     NEXT_PUBLIC_APP_VERSION="${APP_VERSION}" \
     npm run dev) &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "${PID_DIR}/next_dev.pid"
fi

echo ""
echo "════════════════════════════════════════════════"
echo "  iqoqo v${APP_VERSION} ($MODE) servers running"
echo "  Flask API  → http://127.0.0.1:${WEB_PORT}"
if [ "$MODE" == "dev" ]; then
    echo "  Public URL → https://dev.iqoqo.cc"
else
    echo "  Local URL  → http://localhost:3000"
fi
echo "  Press Ctrl+C to stop all servers"
echo "════════════════════════════════════════════════"

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$FLASK_PID" 2>/dev/null
    if [ -d "frontend" ] && [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    rm -f "${PID_DIR}/web_server.pid" "${PID_DIR}/next_dev.pid"
    echo "Stopped."
    exit 0
}

trap cleanup INT TERM
wait
