#!/bin/bash
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

STACK=""
USE_DOCKER=false

usage() {
    echo "Usage: $0 [--stack preview|prod] [--docker]"
    echo ""
    echo "  --stack       Target stack (preview or prod). Default: auto-detect from ENV_FILE in .env"
    echo "  --docker      Run via docker compose exec (default: local .venv)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --stack)
            STACK="$2"
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Determine env file and compose project from stack
if [[ "$STACK" == "preview" ]]; then
    ENV_FILE="$PROJECT_ROOT/.env.preview"
    COMPOSE_PROJECT="iqoqo-preview"
elif [[ "$STACK" == "prod" ]]; then
    if [[ -f "$PROJECT_ROOT/.env.prod" ]]; then
        ENV_FILE="$PROJECT_ROOT/.env.prod"
    else
        ENV_FILE="$PROJECT_ROOT/.env"
    fi
    COMPOSE_PROJECT="iqoqo"
else
    ENV_FILE="$PROJECT_ROOT/.env"
    COMPOSE_PROJECT="iqoqo"
fi

echo "Starting Allegro API OAuth handshake..."
echo "  Stack:    ${STACK:-dev}"
echo "  Env file: ${ENV_FILE}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: Environment file $ENV_FILE not found" >&2
    exit 1
fi

extract_env() {
    local key="$1"
    local env_file="$2"
    grep "^${key}=" "$env_file" 2>/dev/null | head -1 | cut -d'=' -f2- | sed 's/^[[:space:]]*"//;s/"[[:space:]]*$//;s/^[[:space:]]*//;s/[[:space:]]*$//'
}

ALLEGRO_ID=$(extract_env "ALLEGRO_CLIENT_ID" "$ENV_FILE")
ALLEGRO_SECRET=$(extract_env "ALLEGRO_CLIENT_SECRET" "$ENV_FILE")

if [[ -z "$ALLEGRO_ID" ]] || [[ -z "$ALLEGRO_SECRET" ]]; then
    echo "Error: ALLEGRO_CLIENT_ID or ALLEGRO_CLIENT_SECRET is missing in $ENV_FILE" >&2
    exit 1
fi

if [[ "$USE_DOCKER" == "true" ]]; then
    COMPOSE_FILE_ARGS=(-f docker-compose.yml)

    # Detect if running web container uses a prebuilt (ghcr.io) image
    WEB_CONTAINER=$(docker compose -p "$COMPOSE_PROJECT" -f docker-compose.yml ps -q web 2>/dev/null | head -1)
    if [[ -n "$WEB_CONTAINER" ]] && [[ -f "$PROJECT_ROOT/docker-compose.prebuilt.yml" ]]; then
        IMAGE=$(docker inspect "$WEB_CONTAINER" --format '{{.Config.Image}}' 2>/dev/null || true)
        if [[ "$IMAGE" == ghcr.io/* ]]; then
            COMPOSE_FILE_ARGS+=(-f docker-compose.prebuilt.yml)
        fi
    fi

    docker compose -p "$COMPOSE_PROJECT" "${COMPOSE_FILE_ARGS[@]}" exec -T web \
        env PYTHONPATH=. \
        ALLEGRO_CLIENT_ID="$ALLEGRO_ID" \
        ALLEGRO_CLIENT_SECRET="$ALLEGRO_SECRET" \
        python scripts/allegro_auth.py \
    && docker compose -p "$COMPOSE_PROJECT" "${COMPOSE_FILE_ARGS[@]}" up -d --force-recreate web worker
else
    export ALLEGRO_CLIENT_ID="$ALLEGRO_ID"
    export ALLEGRO_CLIENT_SECRET="$ALLEGRO_SECRET"
    cd "$PROJECT_ROOT"
    if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
        .venv/bin/python scripts/allegro_auth.py
    else
        python3 scripts/allegro_auth.py
    fi
fi
