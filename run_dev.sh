#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

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

# 1b. Load environment variables from .env (single source of truth for ports etc.)
if [ -f ".env" ]; then
    # shellcheck disable=SC1091
    set -o allexport
    source .env
    set +o allexport
fi
# WEB_PORT defaults to 5000 if not set in .env
WEB_PORT=${WEB_PORT:-5000}

# 1c. Kill stale processes and remove lock files to allow clean restart
echo "Cleaning up stale processes and locks..."

# Kill anything occupying the Flask API port
if lsof -ti :"${WEB_PORT}" &>/dev/null; then
    echo "  Port ${WEB_PORT} in use — terminating stale process..."
    kill -9 "$(lsof -ti :"${WEB_PORT}")" 2>/dev/null || true
fi

# Kill anything occupying the Next.js port (3000)
NEXT_PORT=${NEXT_PORT:-3000}
if lsof -ti :"${NEXT_PORT}" &>/dev/null; then
    echo "  Port ${NEXT_PORT} in use — terminating stale Next.js process..."
    kill -9 "$(lsof -ti :"${NEXT_PORT}")" 2>/dev/null || true
fi

# Remove stale Next.js dev lock file ("Unable to acquire lock" error)
if [ -f "frontend/.next/dev/lock" ]; then
    echo "  Removing stale Next.js lock file..."
    rm -f "frontend/.next/dev/lock"
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

# 3. Install frontend dependencies if needed
if [ -d "frontend" ] && [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install)
fi

# 4. Run Flask API (background) + Next.js frontend
export FLASK_APP=run.py
export FLASK_DEBUG=1

echo "Starting Flask API at http://127.0.0.1:${WEB_PORT} ..."
flask run --port "${WEB_PORT}" &
FLASK_PID=$!
echo $FLASK_PID > .flask.pid

if [ -d "frontend" ]; then
    echo "Starting Next.js frontend at http://localhost:3000 ..."
    # Pass the API URL derived from WEB_PORT so Next.js picks it up even when
    # frontend/.env.local has a different fallback value.
    (cd frontend && NEXT_PUBLIC_API_URL="http://localhost:${WEB_PORT}" npm run dev) &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > .frontend.pid
fi

echo ""
echo "════════════════════════════════════════════════"
echo "  iqoqo development servers running"
echo "  Flask API  → http://127.0.0.1:${WEB_PORT}"
if [ -d "frontend" ]; then
    echo "  Frontend   → http://localhost:3000"
fi
echo "  Press Ctrl+C to stop all servers"
echo "════════════════════════════════════════════════"

# Wait for Ctrl-C and clean up
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$FLASK_PID" 2>/dev/null
    if [ -d "frontend" ] && [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    rm -f .flask.pid .frontend.pid
    echo "Stopped."
    exit 0
}

trap cleanup INT TERM
wait
