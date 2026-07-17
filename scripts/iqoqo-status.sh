#!/usr/bin/env bash
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
# =============================================================================
# This script renders current iqoqo deployment status
#
set -euo pipefail

IQOQO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
NC=$'\033[0m'

PASS="${GREEN}✅${NC}"
WARN="${YELLOW}⚠️${NC}"
FAIL="${RED}❌${NC}"
INFO="${CYAN}ℹ️ ${NC}"

ERRORS=0
WARNINGS=0

usage() {
    cat <<EOF
Usage: $0 [--stack preview|prod] [--help]

Check health status of all iQoQo services.

Options:
  --stack STACK   Stack to check: preview or prod (default: auto-detect from .env)
  --help          Show this help

Exit codes:
  0   All services healthy
  1   Warnings (non-critical issues)
  2   Errors (critical services down)
EOF
    exit 0
}

STACK=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stack) STACK="$2"; shift 2 ;;
        --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$STACK" ]]; then
    if [[ -f "$IQOQO_ROOT/.env" ]]; then
        ENV_FILE=$(sed -n "s/^[[:space:]]*ENV_FILE=\(.*\)/\1/p" "$IQOQO_ROOT/.env" 2>/dev/null || echo "")
        if [[ "$ENV_FILE" == *".preview"* ]]; then
            STACK="preview"
        elif [[ "$ENV_FILE" == *".prod"* ]]; then
            STACK="prod"
        else
            STACK="prod"
        fi
    else
        STACK="prod"
    fi
fi

if [[ "$STACK" == "preview" ]]; then
    PREFIX="iqoqo-preview"
    ENV_FILE="$IQOQO_ROOT/.env.preview"
    DOMAIN="pre.iqoqo.cc"
else
    PREFIX="iqoqo"
    ENV_FILE="$IQOQO_ROOT/.env"
    DOMAIN="iqoqo.cc"
fi

SERVICES=("nginx" "web" "frontend" "db" "redis" "worker")

if [[ ! -f "$ENV_FILE" ]]; then
    ENV_FILE="$IQOQO_ROOT/.env"
fi

load_env() {
    local key="$1"
    sed -n "s/^[[:space:]]*${key}=\(.*\)/\1/p" "$ENV_FILE" 2>/dev/null | head -1 | tr -d '"' | tr -d "'" || true
}

FRONTEND_URL=$(load_env "NEXT_PUBLIC_FRONTEND_URL")
API_URL=$(load_env "NEXT_PUBLIC_APP_URL")
DB_PORT=$(load_env "DB_PORT")
REDIS_PORT=$(load_env "REDIS_PORT")
NGINX_PORT=$(load_env "NGINX_PORT")

if [[ "$STACK" == "preview" ]]; then
    FRONTEND_URL="${FRONTEND_URL:-https://pre.iqoqo.cc}"
    API_URL="${API_URL:-https://pre.iqoqo.cc}"
    NGINX_PORT="${NGINX_PORT:-8081}"
    DB_PORT="${DB_PORT:-5434}"
    REDIS_PORT="${REDIS_PORT:-6380}"
else
    FRONTEND_URL="${FRONTEND_URL:-https://iqoqo.cc}"
    API_URL="${API_URL:-https://iqoqo.cc}"
    NGINX_PORT="${NGINX_PORT:-8000}"
    DB_PORT="${DB_PORT:-5432}"
    REDIS_PORT="${REDIS_PORT:-6379}"
fi


header() {
    local h="$1"
    printf '\n%s%s%s\n' "$BOLD" "$h" "$NC"
    local i=0; while [ "$i" -lt "${#h}" ]; do printf "─"; i=$((i+1)); done; echo
}

check() {
    local label="$1" status="$2" detail="$3"
    case "$status" in
        pass) printf '  %s %s  %s\n' "$PASS" "$label" "$detail" ;;
        warn) printf '  %s %s  %s\n' "$WARN" "$label" "$detail"; WARNINGS=$((WARNINGS + 1)) ;;
        fail) printf '  %s %s  %s\n' "$FAIL" "$label" "$detail"; ERRORS=$((ERRORS + 1)) ;;
        info) printf '  %s %s  %s\n' "$INFO" "$label" "$detail" ;;
    esac
}

printf "\n"
printf "╔══════════════════════════════════════════════╗\n"
printf '║            %siQoQo Service Status%s              ║\n' "$BOLD" "$NC"
printf '║           %s               ║\n' "$(date '+%Y-%m-%d %H:%M UTC')"
printf '║           Stack: %s%s%s (%s)             ║\n' "$BOLD" "$STACK" "$NC" "$DOMAIN"
printf "╚══════════════════════════════════════════════╝\n"

header "Containers"
for svc in "${SERVICES[@]}"; do
    cname="${PREFIX}-${svc}-1"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$cname"; then
        status_line=$(docker ps --filter "name=${cname}$" --format '{{.Status}}' 2>/dev/null)
        health=$(docker inspect "$cname" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' 2>/dev/null)
        detail="$status_line"
        if [[ "$health" != "no-healthcheck" && "$health" != "" ]]; then
            if [[ "$health" == "healthy" ]]; then
                detail="$detail (health: $health)"
            else
                detail="$detail (health: ${YELLOW}${health}${NC})"
            fi
        fi
        check "$cname" pass "$detail"
    else
        check "$cname" fail "NOT RUNNING"
    fi
done

# Check optional containers (monitoring)
for opt in "openobserve" "otel-collector"; do
    cname="${PREFIX}-${opt}-1"
    cname2="${opt}-1"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -Eq "^(${cname}|${cname2})$"; then
        status_line=$(docker ps --filter "name=${cname}$" --filter "name=${cname2}$" --format '{{.Names}}: {{.Status}}' 2>/dev/null | head -1)
        check "$opt" info "$status_line"
    fi
done

# ─── Redis ──────────────────────────────────────────────────────
header "Redis"
redis_cname="${PREFIX}-redis-1"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$redis_cname"; then
    if ping_result=$(docker exec "$redis_cname" redis-cli ping 2>/dev/null); then
        if [[ "$ping_result" == "PONG" ]]; then
            check "Connectivity" pass "PONG"
            queue_len=$(docker exec "$redis_cname" redis-cli LLEN celery 2>/dev/null || echo "0")
            if [[ "$queue_len" -gt 50 ]]; then
                check "Celery queue" warn "${queue_len} tasks queued (high)"
            elif [[ "$queue_len" -gt 0 ]]; then
                check "Celery queue" info "${queue_len} tasks queued"
            else
                check "Celery queue" pass "empty"
            fi
            mem=$(docker exec "$redis_cname" redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2)
            check "Memory" pass "used${mem:- N/A}"
        else
            check "Connectivity" fail "unexpected response: $ping_result"
        fi
    else
        check "Connectivity" fail "cannot execute redis-cli"
    fi
else
    check "Container" fail "not running"
fi

# ─── PostgreSQL ─────────────────────────────────────────────────
header "PostgreSQL"
db_cname="${PREFIX}-db-1"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$db_cname"; then
    db_user=$(load_env "POSTGRES_USER")
    db_name=$(load_env "POSTGRES_DB")
    db_user="${db_user:-iqoqo}"
    db_name="${db_name:-iqoqo}"
    if docker exec "$db_cname" pg_isready -U "$db_user" -d "$db_name" >/dev/null 2>&1; then
        check "pg_isready" pass "accepting connections"
        schema_count=$(docker exec "$db_cname" psql -U "$db_user" -d "$db_name" -tAc \
            "SELECT count(*) FROM pg_catalog.pg_class JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid WHERE nspname NOT IN ('pg_catalog','information_schema','pg_toast') AND relkind = 'r';" 2>/dev/null || echo "0")
        check "Relations" pass "${schema_count} tables across all schemas"
        # Check for any stuck migrations
        migration_head=$(docker exec "$db_cname" psql -U "$db_user" -d "$db_name" -tAc \
            "SELECT version_num FROM public.alembic_version" 2>/dev/null || echo "N/A")
        check "Migration" pass "version: ${migration_head}"
    else
        check "pg_isready" fail "not accepting connections"
    fi
else
    check "Container" fail "not running"
fi

# ─── Celery Worker ──────────────────────────────────────────────
header "Celery Worker"
worker_cname="${PREFIX}-worker-1"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$worker_cname"; then
    # Check if worker reported "Connected to redis"
    if docker exec "$worker_cname" python3 -c "
import os, redis
r = redis.Redis.from_url(os.environ['REDIS_URL'])
r.ping()
" 2>/dev/null; then
        check "Broker" pass "connected to Redis"
        # Check for recent reconnections (last 5 min)
        recent_reconn=$(docker logs "$worker_cname" --since 5m 2>&1 | grep -c "Connected to redis" || true)
        if [[ "$recent_reconn" -gt 2 ]]; then
            check "Stability" warn "reconnected ${recent_reconn}x in last 5min (flapping?)"
        else
            check "Stability" pass "no recent reconnections"
        fi
        # Check OTel errors in last 2 min (indicates collector down)
        otel_errors=$(docker logs "$worker_cname" --since 2m 2>&1 | grep -c "StatusCode.UNAVAILABLE" || true)
        if [[ "$otel_errors" -gt 10 ]]; then
            check "OTel exporter" warn "${otel_errors} OTel export failures in 2min (collector may be down)"
        else
            check "OTel exporter" pass "no recent export failures"
        fi
        # Check for actual task processing
        tasks_received=$(docker logs "$worker_cname" 2>&1 | grep -c "task received" || true)
        tasks_succeeded=$(docker logs "$worker_cname" 2>&1 | grep -c "succeeded" || true)
        tasks_failed=$(docker logs "$worker_cname" 2>&1 | grep -c "failed" || true)
        check "Tasks" info "received: ~${tasks_received}, succeeded: ~${tasks_succeeded}, failed: ~${tasks_failed}"
    else
        check "Broker" fail "NOT connected to Redis"
    fi
    # Check worker pool type and concurrency
    cmdline=$(docker inspect "$worker_cname" --format '{{.Config.Cmd}}' 2>/dev/null | tr ',' ' ')
    if echo "$cmdline" | grep -q "concurrency"; then
        conc=$(echo "$cmdline" | grep -oP 'concurrency=\K[0-9]+')
        pool=$(echo "$cmdline" | grep -oP 'pool=\K\w+')
        check "Pool" info "--pool=${pool}  --concurrency=${conc}"
    fi
else
    check "Container" fail "not running"
fi

# ─── API Health ─────────────────────────────────────────────────
header "API"
web_cname="${PREFIX}-web-1"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$web_cname"; then
    # Check Flask health endpoint via Python (containers may not have curl)
    health_json=$(docker exec "$web_cname" python3 -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=5)
    print(json.dumps(json.loads(r.read())))
except Exception as e:
    print('ERROR:' + str(e))
" 2>/dev/null || true)
    if echo "$health_json" | grep -qv "^ERROR:"; then
        health_status=$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
        if [[ "$health_status" == "ok" ]]; then
            version=$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
            check "Health endpoint" pass "HTTP 200, status=ok, version=${version}"
        else
            check "Health endpoint" fail "status=${health_status}"
        fi
    else
        health_err="${health_json#ERROR:}"
        check "Health endpoint" fail "${health_err}"
    fi
    # Check gunicorn worker count via /proc (containers may not have pgrep/ps)
    gunicorn_workers=$(docker exec "$web_cname" python3 -c "
import os
count = 0
try:
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                with open(f'/proc/{pid}/cmdline', 'r') as f:
                    cmd = f.read()
                    if 'gunicorn' in cmd and 'master' not in cmd:
                        count += 1
            except (IOError, FileNotFoundError):
                pass
except FileNotFoundError:
    pass
print(count)
" 2>/dev/null || echo "0")
    if [[ "$gunicorn_workers" -ge 2 ]]; then
        check "Gunicorn" pass "${gunicorn_workers} worker processes"
    elif [[ "$gunicorn_workers" -eq 0 ]]; then
        check "Gunicorn" pass "single-process mode"
    else
        check "Gunicorn" info "${gunicorn_workers} worker process(es)"
    fi
else
    check "Container" fail "not running"
fi

# ─── Nginx ──────────────────────────────────────────────────────
header "Nginx & Frontend"
nginx_cname="${PREFIX}-nginx-1"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$nginx_cname"; then
    # Try nginx -t for config syntax
    if docker exec "$nginx_cname" nginx -t 2>&1 | grep -q "test is successful"; then
        check "Config syntax" pass "valid"
    else
        check "Config syntax" fail "INVALID"
    fi

    # Try curl to frontend via nginx
    frontend_code=$(docker exec "$nginx_cname" curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/ 2>/dev/null || echo "000")
    if [[ "$frontend_code" == "200" ]] || [[ "$frontend_code" == "302" ]] || [[ "$frontend_code" == "301" ]]; then
        check "Frontend (via nginx)" pass "HTTP ${frontend_code}"
    else
        check "Frontend (via nginx)" fail "HTTP ${frontend_code}"
    fi

    # Try /api/health through nginx proxy
    api_code=$(docker exec "$nginx_cname" curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/health 2>/dev/null || echo "000")
    if [[ "$api_code" == "200" ]]; then
        check "API proxy (via nginx)" pass "HTTP ${api_code}"
    else
        check "API proxy (via nginx)" fail "HTTP ${api_code}"
    fi

    # Check for recent 5xx errors in nginx logs
    recent_5xx=$(docker logs "$nginx_cname" --since 15m 2>&1 | grep -c '" 5[0-9][0-9] ' || true)
    if [[ "$recent_5xx" -gt 10 ]]; then
        check "Recent 5xx errors" warn "${recent_5xx} in last 15min"
    else
        check "Recent 5xx errors" pass "${recent_5xx} in last 15min"
    fi
else
    check "Container" fail "not running"
fi

# ─── Covers Directory ──────────────────────────────────────────
header "Covers"
covers_dir="$IQOQO_ROOT/app/static/covers"
if [[ -d "$covers_dir" ]]; then
    cover_count=$(find "$covers_dir" -maxdepth 1 -type f 2>/dev/null | wc -l)
    cover_size=$(du -sh "$covers_dir" 2>/dev/null | cut -f1)
    # Check for covers created in last hour
    recent_covers=$(find "$covers_dir" -maxdepth 1 -type f -newer "$covers_dir" -mmin -60 2>/dev/null | wc -l)
    check "Directory" pass "${cover_count} files, ${cover_size}"
    if [[ "$recent_covers" -gt 0 ]]; then
        check "Recent activity" pass "${recent_covers} new files in last hour"
    else
        check "Recent activity" info "no new files in last hour"
    fi
    # Check for broken/empty files
    empty_covers=$(find "$covers_dir" -maxdepth 1 -type f -size -1k 2>/dev/null | wc -l)
    if [[ "$empty_covers" -gt 0 ]]; then
        check "Empty files" warn "${empty_covers} files < 1KB (possibly broken)"
    fi
    # Check database cover pipeline status
    db_cname="${PREFIX}-db-1"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$db_cname"; then
        db_user=$(load_env "POSTGRES_USER")
        db_name=$(load_env "POSTGRES_DB")
        db_user="${db_user:-iqoqo}"
        db_name="${db_name:-iqoqo}"
        cover_status_data=$(docker exec "$db_cname" psql -U "$db_user" -d "$db_name" -tAc \
            "SELECT COALESCE(meta->>'cover_status', 'not_started'), count(*) FROM manifestations GROUP BY 1;" 2>/dev/null || echo "")
        if [[ -n "$cover_status_data" ]]; then
            ready_cnt=$(echo "$cover_status_data" | grep "^ready" | cut -f2 -d'|' || echo "0")
            pending_cnt=$(echo "$cover_status_data" | grep "^pending" | cut -f2 -d'|' || echo "0")
            processing_cnt=$(echo "$cover_status_data" | grep "^processing" | cut -f2 -d'|' || echo "0")
            failed_cnt=$(echo "$cover_status_data" | grep "^failed" | cut -f2 -d'|' || echo "0")

            ready_cnt="${ready_cnt:-0}"
            pending_cnt="${pending_cnt:-0}"
            processing_cnt="${processing_cnt:-0}"
            failed_cnt="${failed_cnt:-0}"

            check "Database pipeline" pass "ready: ${ready_cnt}, pending: ${pending_cnt}, processing: ${processing_cnt}, failed: ${failed_cnt}"

            stuck=$((pending_cnt + processing_cnt))
            if [[ "$stuck" -gt 0 ]]; then
                check "Stuck tasks" warn "${stuck} cover task(s) in flight/stuck"
            fi
        fi
    fi
else
    check "Directory" fail "NOT FOUND at ${covers_dir}"
fi

# ─── Allegro API ───────────────────────────────────────────────
header "Allegro API"
client_id=$(load_env "ALLEGRO_CLIENT_ID")
client_secret=$(load_env "ALLEGRO_CLIENT_SECRET")
if [[ -z "$client_id" || -z "$client_secret" ]]; then
    check "Status" info "not configured (missing credentials in .env)"
elif [[ ! -f "$IQOQO_ROOT/.allegro_token.json" ]]; then
    check "Status" warn "configured but not active (OAuth handshake pending)"
else
    token_age_hours=0
    token_valid=false
    if command -v python3 &>/dev/null; then
        token_result=$(python3 -c "
import json, os, time
try:
    with open('$IQOQO_ROOT/.allegro_token.json') as f:
        t = json.load(f)
    if not t.get('access_token'):
        print('EMPTY')
    else:
        age = time.time() - os.path.getmtime('$IQOQO_ROOT/.allegro_token.json')
        print(int(age))
except Exception:
    print('ERROR')
" 2>/dev/null || echo 'ERROR')
        if [[ "$token_result" =~ ^[0-9]+$ ]]; then
            token_valid=true
            token_age_hours=$((token_result / 3600))
        fi
    fi
    if [[ "$token_valid" != true ]]; then
        check "Status" warn "not active (placeholder or missing token, re-run: make allegro-auth <stack> USE_DOCKER=true)"
    elif [[ "$token_age_hours" -gt 12 ]]; then
        check "Status" warn "token expired (${token_age_hours}h old, re-run: make allegro-auth <stack> USE_DOCKER=true)"
    else
        check "Status" pass "active (token age: ${token_age_hours}h)"
    fi
fi

# ─── Environment Configuration ──────────────────────────────────
header "Environment Configuration"

# Read expected keys from .env.example
EXAMPLE_FILE="$IQOQO_ROOT/.env.example"
if [[ -f "$EXAMPLE_FILE" ]]; then
    expected_keys=()
    declare -A example_defaults
    while IFS='=' read -r key val; do
        [[ -z "$key" || "$key" == \#* ]] && continue
        val=$(echo "$val" | sed 's/[[:space:]]*#.*$//;s/^[[:space:]]*"//;s/"[[:space:]]*$//;s/^[[:space:]]*//;s/[[:space:]]*$//')
        expected_keys+=("$key")
        if [[ -z "$val" ]]; then
            example_defaults["$key"]="empty"
        else
            example_defaults["$key"]="set"
        fi
    done < "$EXAMPLE_FILE"
else
    check "Template" warn ".env.example not found"
    expected_keys=()
    declare -A example_defaults
fi

total_expected=${#expected_keys[@]}
missing_warn=0
missing_info=0
empty_count=0
active_count=0
missing_warn_vars=()
missing_info_vars=()
empty_vars=()

for key in "${expected_keys[@]}"; do
    val=$(load_env "$key")
    if [[ -n "$val" ]]; then
        active_count=$((active_count + 1))
    elif [[ "$val" == "" ]] && grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        empty_count=$((empty_count + 1))
        empty_vars+=("$key")
    else
        if [[ "${example_defaults[$key]:-set}" == "empty" ]]; then
            missing_info=$((missing_info + 1))
            missing_info_vars+=("$key")
        else
            missing_warn=$((missing_warn + 1))
            missing_warn_vars+=("$key")
        fi
    fi
done

check "Configured" pass "${active_count} of ${total_expected} variables present"

if [[ "$missing_warn" -gt 0 ]]; then
    check "Missing" warn "${missing_warn} variable(s): ${missing_warn_vars[*]}"
fi

if [[ "$missing_info" -gt 0 ]]; then
    check "Optional" info "${missing_info} variable(s) (not configured): ${missing_info_vars[*]}"
fi

if [[ "$empty_count" -gt 0 ]]; then
    check "Empty" info "${empty_count} variable(s) (intentional): ${empty_vars[*]}"
fi

# Danger zone: values that silently disable features
otel_traces=$(load_env "OTEL_TRACES_EXPORTER")
otel_logs=$(load_env "OTEL_LOGS_EXPORTER")
otel_metrics=$(load_env "OTEL_METRICS_EXPORTER")
otel_disabled=()
[[ "$otel_traces" == "none" || -z "$otel_traces" ]] && otel_disabled+=("traces")
[[ "$otel_logs"   == "none" || -z "$otel_logs"   ]] && otel_disabled+=("logs")
[[ "$otel_metrics" == "none" || -z "$otel_metrics" ]] && otel_disabled+=("metrics")
if [[ ${#otel_disabled[@]} -gt 0 ]]; then
    check "Observability" warn "OTel exporters set to 'none' for: ${otel_disabled[*]}"
fi

# ─── Disk Usage ─────────────────────────────────────────────────
header "Disk"
docker_root=$(docker info 2>/dev/null | grep "Docker Root Dir" | awk -F: '{print $2}' | tr -d ' ' || echo "/var/lib/docker")
if [[ -d "$docker_root" ]]; then
    disk_usage=$(df -h "$docker_root" 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%' || echo "0")
    if [[ "$disk_usage" -gt 90 ]]; then
        check "Docker root ($docker_root)" fail "${disk_usage}% used"
    elif [[ "$disk_usage" -gt 80 ]]; then
        check "Docker root ($docker_root)" warn "${disk_usage}% used"
    else
        check "Docker root ($docker_root)" pass "${disk_usage}% used"
    fi
fi
# Check project root disk
root_usage=$(df -h "$IQOQO_ROOT" 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%' || echo "0")
if [[ "$root_usage" -gt 90 ]]; then
    check "Project root ($IQOQO_ROOT)" fail "${root_usage}% used"
elif [[ "$root_usage" -gt 80 ]]; then
    check "Project root ($IQOQO_ROOT)" warn "${root_usage}% used"
else
    check "Project root ($IQOQO_ROOT)" pass "${root_usage}% used"
fi

# ─── Docker System ──────────────────────────────────────────────
header "Docker System"
engine_ok=$(docker info 2>/dev/null | grep -c "WARNING" || true)
if [[ "$engine_ok" -eq 0 ]]; then
    check "Engine" pass "no warnings"
else
    docker info 2>/dev/null | grep "WARNING" | while IFS= read -r line; do
        check "Warning" warn "$line"
    done
fi
# Running containers count
total_containers=$(docker ps -q 2>/dev/null | wc -l)
check "Containers" info "${total_containers} total running"

# ─── Summary ────────────────────────────────────────────────────
printf "\n┌──────────────────────────────────────────────────────────┐\n"
if [[ "$ERRORS" -gt 0 ]]; then
    printf '│ %s  %sSTATUS: %s%s error(s)%s' "$FAIL" "$BOLD" "$RED" "$ERRORS" "$NC"
    [[ "$WARNINGS" -gt 0 ]] && printf ', %s%s warning(s)%s' "$YELLOW" "$WARNINGS" "$NC"
    printf " found                        │\n"
    exit_code=2
elif [[ "$WARNINGS" -gt 0 ]]; then
    printf '│ %s  %sSTATUS: %s%s warning(s)%s, no errors                    │\n' "$WARN" "$BOLD" "$YELLOW" "$WARNINGS" "$NC"
    exit_code=1
else
    printf '│ %s  %sSTATUS: %sAll services healthy%s                         │\n' "$PASS" "$BOLD" "$GREEN" "$NC"
    exit_code=0
fi
printf "└──────────────────────────────────────────────────────────┘\n"
printf "\n"

exit "$exit_code"
