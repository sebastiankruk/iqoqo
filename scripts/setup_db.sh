#!/usr/bin/env bash
# =============================================================================
# scripts/setup_db.sh
#
# Ensures the PostgreSQL database and role defined in .env exist and have the
# correct privileges.
#
# WHY THIS EXISTS
# ---------------
# When a Docker volume is created from a previous run (or a different host
# machine), the POSTGRES_USER init env-var is silently ignored by PostgreSQL
# because it only runs the init scripts on first start with an empty data dir.
# This means the role name in .env may differ from the one actually in the
# volume's pg_authid table, causing "role does not exist" errors.
#
# This script detects the actual superuser inside the running container,
# then creates the expected application role if it is missing.
#
# USAGE
# -----
#   bash scripts/setup_db.sh          # called automatically by run_dev.sh
#   bash scripts/setup_db.sh --check  # only test connectivity, no changes
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Load environment
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "${ROOT_DIR}/.env" ]; then
    # shellcheck disable=SC1091
    set -o allexport
    source "${ROOT_DIR}/.env"
    set +o allexport
fi

# Defaults (mirror .env.example values)
POSTGRES_USER="${POSTGRES_USER:-iqoqo}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-changeme_strong_password}"
POSTGRES_DB="${POSTGRES_DB:-iqoqo}"
DB_PORT="${DB_PORT:-5432}"
DB_HOST="${DB_HOST:-localhost}"

CHECK_ONLY="${1:-}"

# ---------------------------------------------------------------------------
# 1. Find the running DB container
# ---------------------------------------------------------------------------
find_container() {
    # Try the default compose-v2 name first, then any container with 'db' in
    # its name that exposes the expected port.
    local candidate
    candidate=$(docker ps --format "{{.Names}}" \
        | grep -E "^${COMPOSE_PROJECT_NAME:-iqoqo}[-_]db[-_]?[0-9]*$" \
        | head -1 2>/dev/null || true)

    if [ -z "$candidate" ]; then
        candidate=$(docker ps --format "{{.Names}}" \
            | grep "\-db-\|_db_\|-db$\|_db$" \
            | head -1 2>/dev/null || true)
    fi
    echo "$candidate"
}

# ---------------------------------------------------------------------------
# 2. Find a working superuser inside the container
# ---------------------------------------------------------------------------
find_superuser() {
    local container="$1"
    # The superuser name can differ depending on which POSTGRES_USER was set
    # when the volume was first initialised.  Try the most common candidates.
    local candidates=("$POSTGRES_USER" "postgres" "user" "admin")
    for u in "${candidates[@]}"; do
        if docker exec "$container" psql -U "$u" -d postgres -c "" &>/dev/null 2>&1; then
            echo "$u"
            return 0
        fi
        # Some images default the DB name to the user name instead of 'postgres'
        if docker exec "$container" psql -U "$u" -d "$u" -c "" &>/dev/null 2>&1; then
            echo "$u"
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# 3. Check if the application role already exists
# ---------------------------------------------------------------------------
role_exists() {
    local container="$1"
    local superuser="$2"
    local role="$3"
    docker exec "$container" psql -U "$superuser" -d postgres \
        -tAc "SELECT 1 FROM pg_roles WHERE rolname = '${role}'" 2>/dev/null \
        | grep -q "^1$"
}

# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
echo "Checking database role '${POSTGRES_USER}'..."

CONTAINER=$(find_container)
if [ -z "$CONTAINER" ]; then
    echo "  No running DB container found — skipping role check."
    exit 0
fi

if [ "$CHECK_ONLY" = "--check" ]; then
    echo "  Container: ${CONTAINER}"
    SUPERUSER=$(find_superuser "$CONTAINER" 2>/dev/null || true)
    echo "  Detected superuser: ${SUPERUSER:-unknown}"
    if role_exists "$CONTAINER" "${SUPERUSER}" "${POSTGRES_USER}"; then
        echo "  Role '${POSTGRES_USER}' EXISTS ✓"
    else
        echo "  Role '${POSTGRES_USER}' MISSING ✗"
    fi
    exit 0
fi

SUPERUSER=$(find_superuser "$CONTAINER" 2>/dev/null || true)
if [ -z "$SUPERUSER" ]; then
    echo "  Could not identify a superuser in container '${CONTAINER}' — skipping."
    exit 0
fi

if role_exists "$CONTAINER" "$SUPERUSER" "$POSTGRES_USER"; then
    echo "  Role '${POSTGRES_USER}' already exists. ✓"
    exit 0
fi

echo "  Role '${POSTGRES_USER}' missing in container '${CONTAINER}' (superuser: '${SUPERUSER}')."
echo "  Creating role and granting privileges..."

docker exec "$CONTAINER" psql -U "$SUPERUSER" -d postgres \
    -v "app_user=${POSTGRES_USER}" \
    -v "app_pass=${POSTGRES_PASSWORD}" <<'SQL'
SELECT format('CREATE USER %I WITH PASSWORD %L', :'app_user', :'app_pass') \gexec
SQL

docker exec "$CONTAINER" psql -U "$SUPERUSER" -d postgres \
    -v "app_db=${POSTGRES_DB}" \
    -v "app_user=${POSTGRES_USER}" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'app_db', :'app_user') \gexec
SQL
2>/dev/null || echo "  (Database '${POSTGRES_DB}' already exists — continuing.)"

docker exec "$CONTAINER" psql -U "$SUPERUSER" -d "$POSTGRES_DB" \
    -v "app_db=${POSTGRES_DB}" \
    -v "app_user=${POSTGRES_USER}" <<'SQL'
SELECT format('GRANT ALL PRIVILEGES ON DATABASE %I TO %I', :'app_db', :'app_user') \gexec;
SELECT format('GRANT ALL ON SCHEMA public TO %I', :'app_user') \gexec;
SELECT format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', :'app_user') \gexec;
SELECT format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %I', :'app_user') \gexec;
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO %I', :'app_user') \gexec;
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO %I', :'app_user') \gexec;
SQL
2>&1

echo "  Role '${POSTGRES_USER}' created and privileges granted. ✓"
