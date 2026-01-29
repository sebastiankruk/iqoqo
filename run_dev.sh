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

# 3. Run Flask Application
export FLASK_APP=run.py
export FLASK_DEBUG=1
echo "Starting Flask server at http://127.0.0.1:5000 ..."
flask run