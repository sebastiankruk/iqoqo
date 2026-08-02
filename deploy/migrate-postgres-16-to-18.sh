#!/usr/bin/env bash
# deploy/migrate-postgres-16-to-18.sh
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
# ------------------------------------------------------------------
# Safe PostgreSQL 16 → 18 data migration for iqoqo Docker stacks.
#
# Usage:
#   ./deploy/migrate-postgres-16-to-18.sh <stack>
#
# Supported stacks:
#   dev      → volume iqoqo-dev_postgres_data
#   preview  → volume iqoqo-preview_postgres_data
#   prod     → volume iqoqo_postgres_data
#
# This script does NOT rely on docker-compose.yml still pointing to
# postgres:16. It spins up a standalone postgres:16-alpine container
# to read the old data, so it works even after `git pull` has already
# updated the compose file to postgres:18-alpine.
# ------------------------------------------------------------------
set -euo pipefail

# --------------- constants ---------------
readonly OLD_PG_IMAGE="postgres:16-alpine"
readonly NEW_PG_IMAGE="postgres:18-alpine"
readonly PG_DATA_DIR="/var/lib/postgresql/data"
readonly DUMP_FILENAME="iqoqo_pg16_dump.sql"
readonly MIGRATION_CONTAINER_PREFIX="iqoqo-pg-migrate"

# --------------- colours (if tty) --------
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; NC=''
fi

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()   { error "$@"; exit 1; }

# --------------- usage -------------------
usage() {
  cat <<EOF
Usage: $(basename "$0") <stack> [options]

Stacks:  dev | preview | prod

Options:
  --pg-user <user>       Postgres user (default: from .env or 'iqoqo')
  --pg-password <pass>   Postgres password (default: from .env or 'changeme')
  --pg-db <db>           Postgres database (default: from .env or 'iqoqo')
  --dry-run              Show what would be done without executing
  --skip-pull            Skip pulling Docker images
  -h, --help             Show this help

Examples:
  # Migrate the preview stack
  ./deploy/migrate-postgres-16-to-18.sh preview

  # Migrate prod after git pull
  ./deploy/migrate-postgres-16-to-18.sh prod

  # Dry run on dev
  ./deploy/migrate-postgres-16-to-18.sh dev --dry-run
EOF
  exit 0
}

# --------------- arg parsing -------------
STACK=""
DRY_RUN=false
SKIP_PULL=false
PG_USER=""
PG_PASSWORD=""
PG_DB=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    dev|preview|prod) STACK="$1"; shift ;;
    --pg-user)     PG_USER="$2"; shift 2 ;;
    --pg-password) PG_PASSWORD="$2"; shift 2 ;;
    --pg-db)       PG_DB="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --skip-pull)   SKIP_PULL=true; shift ;;
    -h|--help)     usage ;;
    *)             die "Unknown argument: $1. Run with --help for usage." ;;
  esac
done

[[ -z "$STACK" ]] && die "Stack name required. Usage: $(basename "$0") <dev|preview|prod>"

# --------------- resolve volume name -----
resolve_volume_name() {
  local stack="$1"
  case "$stack" in
    prod)    echo "iqoqo_postgres_data" ;;
    preview) echo "iqoqo-preview_postgres_data" ;;
    dev)     echo "iqoqo-dev_postgres_data" ;;
    *)       die "Unknown stack: $stack" ;;
  esac
}

# --------------- resolve env file --------
resolve_env_file() {
  local stack="$1"
  case "$stack" in
    prod)    echo ".env.prod" ;;
    preview) echo ".env.preview" ;;
    dev)     echo ".env" ;;
    *)       echo ".env" ;;
  esac
}

# --------------- load credentials --------
load_credentials() {
  local env_file
  env_file="$(resolve_env_file "$STACK")"

  # Fall back to .env if stack-specific file doesn't exist
  if [[ ! -f "$env_file" ]] && [[ -f ".env" ]]; then
    env_file=".env"
  fi

  if [[ -f "$env_file" ]]; then
    info "Loading credentials from $env_file"
    # shellcheck disable=SC1090
    set -a; source "$env_file" 2>/dev/null || true; set +a
  fi

  PG_USER="${PG_USER:-${POSTGRES_USER:-iqoqo}}"
  PG_PASSWORD="${PG_PASSWORD:-${POSTGRES_PASSWORD:-changeme}}"
  PG_DB="${PG_DB:-${POSTGRES_DB:-iqoqo}}"
}

# --------------- pre-flight checks -------
preflight() {
  command -v docker >/dev/null 2>&1 || die "docker is not installed or not in PATH."

  VOLUME_NAME="$(resolve_volume_name "$STACK")"
  BACKUP_VOLUME="${VOLUME_NAME}_v16_backup"
  DUMP_DIR="$(mktemp -d)"
  DUMP_PATH="${DUMP_DIR}/${DUMP_FILENAME}"

  info "Stack:         $STACK"
  info "Source volume:  $VOLUME_NAME"
  info "Backup volume:  $BACKUP_VOLUME"
  info "Postgres user:  $PG_USER"
  info "Postgres DB:    $PG_DB"
  info "Dump location:  $DUMP_PATH"
  echo ""

  # Check the source volume exists
  if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    die "Volume '$VOLUME_NAME' does not exist. Nothing to migrate."
  fi

  # Check that no containers are using the volume
  local containers_using_volume
  containers_using_volume=$(docker ps -q --filter "volume=${VOLUME_NAME}" 2>/dev/null || true)
  if [[ -n "$containers_using_volume" ]]; then
    die "Volume '$VOLUME_NAME' is in use by running container(s). Stop the stack first:\n  make stop $STACK"
  fi

  # Check if backup volume already exists (previous migration attempt)
  if docker volume inspect "$BACKUP_VOLUME" >/dev/null 2>&1; then
    warn "Backup volume '$BACKUP_VOLUME' already exists from a previous migration."
    warn "If you want to re-migrate from the original v16 data, remove it first:"
    warn "  docker volume rm $BACKUP_VOLUME"
    echo ""
    read -r -p "Continue with migration from current '$VOLUME_NAME'? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || die "Migration cancelled."
  fi
}

# --------------- pull images -------------
pull_images() {
  if [[ "$SKIP_PULL" == "true" ]]; then
    info "Skipping image pull (--skip-pull)"
    return
  fi
  info "Pulling $OLD_PG_IMAGE for dump..."
  docker pull "$OLD_PG_IMAGE"
  info "Pulling $NEW_PG_IMAGE for restore..."
  docker pull "$NEW_PG_IMAGE"
}

# --------------- step 1: dump v16 --------
dump_v16() {
  info "=== Step 1/4: Dumping data from v16 volume ==="

  local container_name="${MIGRATION_CONTAINER_PREFIX}-dump-$$"

  info "Starting temporary $OLD_PG_IMAGE container..."
  docker run -d \
    --name "$container_name" \
    -v "${VOLUME_NAME}:${PG_DATA_DIR}" \
    -e POSTGRES_USER="$PG_USER" \
    -e POSTGRES_PASSWORD="$PG_PASSWORD" \
    -e POSTGRES_DB="$PG_DB" \
    "$OLD_PG_IMAGE" >/dev/null

  # Wait for postgres to be ready
  info "Waiting for PostgreSQL 16 to become ready..."
  local retries=30
  while ! docker exec "$container_name" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; do
    retries=$((retries - 1))
    if [[ $retries -le 0 ]]; then
      docker rm -f "$container_name" >/dev/null 2>&1 || true
      die "PostgreSQL 16 failed to start within 30 seconds."
    fi
    sleep 1
  done
  info "PostgreSQL 16 is ready."

  info "Running pg_dumpall..."
  docker exec "$container_name" pg_dumpall -U "$PG_USER" > "$DUMP_PATH"

  local dump_size
  dump_size=$(du -h "$DUMP_PATH" | cut -f1)
  info "Dump complete: $DUMP_PATH ($dump_size)"

  info "Stopping temporary container..."
  docker rm -f "$container_name" >/dev/null 2>&1
}

# --------------- step 2: backup volume ---
backup_volume() {
  info "=== Step 2/4: Backing up v16 volume ==="

  # Rename the old volume by creating a new one and copying data
  info "Creating backup volume '$BACKUP_VOLUME'..."
  docker volume create "$BACKUP_VOLUME" >/dev/null

  info "Copying data from '$VOLUME_NAME' to '$BACKUP_VOLUME'..."
  docker run --rm \
    -v "${VOLUME_NAME}:/source:ro" \
    -v "${BACKUP_VOLUME}:/dest" \
    alpine sh -c "cp -a /source/. /dest/"

  info "Backup complete."

  info "Removing old volume '$VOLUME_NAME'..."
  docker volume rm "$VOLUME_NAME"
  info "Old volume removed."
}

# --------------- step 3: restore to v18 --
restore_v18() {
  info "=== Step 3/4: Restoring data to v18 ==="

  local container_name="${MIGRATION_CONTAINER_PREFIX}-restore-$$"

  # Docker Compose will recreate this volume on next `up`
  info "Creating fresh volume '$VOLUME_NAME'..."
  docker volume create "$VOLUME_NAME" >/dev/null

  info "Starting temporary $NEW_PG_IMAGE container..."
  docker run -d \
    --name "$container_name" \
    -v "${VOLUME_NAME}:${PG_DATA_DIR}" \
    -v "${DUMP_DIR}:/dump:ro" \
    -e POSTGRES_USER="$PG_USER" \
    -e POSTGRES_PASSWORD="$PG_PASSWORD" \
    -e POSTGRES_DB="$PG_DB" \
    "$NEW_PG_IMAGE" >/dev/null

  # Wait for postgres to be ready
  info "Waiting for PostgreSQL 18 to become ready..."
  local retries=30
  while ! docker exec "$container_name" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; do
    retries=$((retries - 1))
    if [[ $retries -le 0 ]]; then
      docker rm -f "$container_name" >/dev/null 2>&1 || true
      die "PostgreSQL 18 failed to start within 30 seconds."
    fi
    sleep 1
  done
  info "PostgreSQL 18 is ready."

  info "Restoring dump into PostgreSQL 18..."
  docker exec -i "$container_name" psql -U "$PG_USER" -d "$PG_DB" < "$DUMP_PATH"

  info "Restore complete."

  info "Stopping temporary container..."
  docker rm -f "$container_name" >/dev/null 2>&1
}

# --------------- step 4: cleanup ---------
cleanup() {
  info "=== Step 4/4: Cleanup ==="

  if [[ -f "$DUMP_PATH" ]]; then
    info "Removing temporary dump file..."
    rm -f "$DUMP_PATH"
    rmdir "$DUMP_DIR" 2>/dev/null || true
  fi

  info "Cleanup complete."
}

# --------------- dry run -----------------
dry_run_report() {
  VOLUME_NAME="$(resolve_volume_name "$STACK")"
  BACKUP_VOLUME="${VOLUME_NAME}_v16_backup"

  echo ""
  info "=== DRY RUN — no changes will be made ==="
  echo ""
  echo "  1. Pull images: $OLD_PG_IMAGE, $NEW_PG_IMAGE"
  echo "  2. Start temporary $OLD_PG_IMAGE container with volume '$VOLUME_NAME'"
  echo "  3. Run pg_dumpall to a temporary file"
  echo "  4. Stop temporary container"
  echo "  5. Create backup volume '$BACKUP_VOLUME'"
  echo "  6. Copy data from '$VOLUME_NAME' → '$BACKUP_VOLUME'"
  echo "  7. Remove volume '$VOLUME_NAME'"
  echo "  8. Create fresh volume '$VOLUME_NAME'"
  echo "  9. Start temporary $NEW_PG_IMAGE container with new volume"
  echo "  10. Restore dump into PostgreSQL 18"
  echo "  11. Stop temporary container"
  echo "  12. Clean up temporary files"
  echo ""
  info "After migration, start the stack with:"
  echo "  make start $STACK prebuilt    # for prebuilt images"
  echo "  make start $STACK             # for local build"
  echo ""
  info "To roll back (if needed):"
  echo "  docker volume rm $VOLUME_NAME"
  echo "  docker volume create $VOLUME_NAME"
  echo "  docker run --rm -v ${BACKUP_VOLUME}:/src:ro -v ${VOLUME_NAME}:/dst alpine sh -c 'cp -a /src/. /dst/'"
  echo ""
}

# --------------- main --------------------
main() {
  echo ""
  info "╔══════════════════════════════════════════════════════════════╗"
  info "║    iqoqo PostgreSQL 16 → 18 Migration                     ║"
  info "║    Stack: $STACK                                           ║"
  info "╚══════════════════════════════════════════════════════════════╝"
  echo ""

  load_credentials

  if [[ "$DRY_RUN" == "true" ]]; then
    dry_run_report
    exit 0
  fi

  preflight
  pull_images
  dump_v16
  backup_volume
  restore_v18
  cleanup

  echo ""
  info "╔══════════════════════════════════════════════════════════════╗"
  info "║    Migration complete! 🎉                                  ║"
  info "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  info "Your v16 data is safely backed up in volume: $BACKUP_VOLUME"
  info ""
  info "Next steps:"
  info "  make start $STACK prebuilt    # for prebuilt images"
  info "  make start $STACK             # for local build"
  echo ""
  info "To roll back (if needed):"
  info "  docker volume rm $VOLUME_NAME"
  info "  docker volume create $VOLUME_NAME"
  info "  docker run --rm -v ${BACKUP_VOLUME}:/src:ro -v ${VOLUME_NAME}:/dst alpine sh -c 'cp -a /src/. /dst/'"
  echo ""
}

main
