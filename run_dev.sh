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

echo "Starting Flask API at http://127.0.0.1:5000 ..."
flask run --port 5000 &
FLASK_PID=$!
echo $FLASK_PID > .flask.pid

if [ -d "frontend" ]; then
    echo "Starting Next.js frontend at http://localhost:3000 ..."
    (cd frontend && npm run dev) &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > .frontend.pid
fi

echo ""
echo "════════════════════════════════════════════════"
echo "  iqoqo development servers running"
echo "  Flask API  → http://127.0.0.1:5000"
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