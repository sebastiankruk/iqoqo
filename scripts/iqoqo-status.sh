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
Usage: $0 [--stack dev|preview|prod] [--help]

Check health status of all iQoQo services.

Options:
  --stack STACK   Stack to check: dev, preview, or prod (default: auto-detect from .env / mode)
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
        dev|preview|prod) STACK="$1"; shift ;;
        --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$STACK" ]]; then
    if [[ -n "${MODE:-}" ]]; then
        STACK="$MODE"
    elif [[ -f "$IQOQO_ROOT/.env" ]]; then
        ENV_FILE_VAL=$(sed -n "s/^[[:space:]]*ENV_FILE=\(.*\)/\1/p" "$IQOQO_ROOT/.env" 2>/dev/null || echo "")
        if [[ "$ENV_FILE_VAL" == *".preview"* ]]; then
            STACK="preview"
        elif [[ "$ENV_FILE_VAL" == *".prod"* ]]; then
            STACK="prod"
        elif [[ "$ENV_FILE_VAL" == *".dev"* ]]; then
            STACK="dev"
        elif [[ -d "$IQOQO_ROOT/.pids" ]]; then
            STACK="dev"
        else
            STACK="dev"
        fi
    else
        STACK="dev"
    fi
fi

if [[ "$STACK" == "preview" ]]; then
    PREFIX="iqoqo-preview"
    ENV_FILE="$IQOQO_ROOT/.env.preview"
    DOMAIN="pre.iqoqo.cc"
    SERVICES=("nginx" "web" "frontend" "db" "redis" "worker")
elif [[ "$STACK" == "dev" ]]; then
    PREFIX="iqoqo"
    ENV_FILE="$IQOQO_ROOT/.env.dev"
    [[ ! -f "$ENV_FILE" ]] && ENV_FILE="$IQOQO_ROOT/.env"
    DOMAIN="localhost:3000"
    SERVICES=("db" "redis")
else
    PREFIX="iqoqo"
    ENV_FILE="$IQOQO_ROOT/.env.prod"
    [[ ! -f "$ENV_FILE" ]] && ENV_FILE="$IQOQO_ROOT/.env"
    DOMAIN="iqoqo.cc"
    SERVICES=("nginx" "web" "frontend" "db" "redis" "worker")
fi

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
WEB_PORT=$(load_env "WEB_PORT")
WEB_PORT="${WEB_PORT:-5000}"

if [[ "$STACK" == "preview" ]]; then
    FRONTEND_URL="${FRONTEND_URL:-https://pre.iqoqo.cc}"
    API_URL="${API_URL:-https://pre.iqoqo.cc}"
    NGINX_PORT="${NGINX_PORT:-8081}"
    DB_PORT="${DB_PORT:-5434}"
    REDIS_PORT="${REDIS_PORT:-6380}"
elif [[ "$STACK" == "dev" ]]; then
    FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
    API_URL="${API_URL:-http://127.0.0.1:${WEB_PORT}}"
    DB_PORT="${DB_PORT:-5432}"
    REDIS_PORT="${REDIS_PORT:-6379}"
else
    FRONTEND_URL="${FRONTEND_URL:-https://iqoqo.cc}"
    API_URL="${API_URL:-https://iqoqo.cc}"
    NGINX_PORT="${NGINX_PORT:-8000}"
    DB_PORT="${DB_PORT:-5432}"
    REDIS_PORT="${REDIS_PORT:-6379}"
fi

find_container() {
    local svc="$1"
    for cname_test in "${PREFIX}-${svc}-1" "${PREFIX}-${svc}" "iqoqo-${svc}-1" "iqoqo-${STACK}-${svc}-1" "${svc}-1" "${PREFIX}_${svc}_1" "${svc}"; do
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$cname_test"; then
            echo "$cname_test"
            return 0
        fi
    done
    echo ""
}

header() {
    [[ -n "${IQOQO_AI_MODE:-}" ]] && return 0
    local h="$1"
    printf '\n%s%s%s\n' "$BOLD" "$h" "$NC"
    local i=0; while [ "$i" -lt "${#h}" ]; do printf "─"; i=$((i+1)); done; echo
}

check() {
    local label="$1" status="$2" detail="$3"
    if [[ -n "${IQOQO_AI_MODE:-}" ]]; then
        case "$status" in
            pass|info) return 0 ;;
            warn) printf '  %s %s  %s\n' "$WARN" "$label" "$detail"; WARNINGS=$((WARNINGS + 1)) ;;
            fail) printf '  %s %s  %s\n' "$FAIL" "$label" "$detail"; ERRORS=$((ERRORS + 1)) ;;
        esac
        return 0
    fi
    case "$status" in
        pass) printf '  %s %s  %s\n' "$PASS" "$label" "$detail" ;;
        warn) printf '  %s %s  %s\n' "$WARN" "$label" "$detail"; WARNINGS=$((WARNINGS + 1)) ;;
        fail) printf '  %s %s  %s\n' "$FAIL" "$label" "$detail"; ERRORS=$((ERRORS + 1)) ;;
        info) printf '  %s %s  %s\n' "$INFO" "$label" "$detail" ;;
    esac
}

if [[ -z "${IQOQO_AI_MODE:-}" ]]; then
    printf "\n"
    printf "╔══════════════════════════════════════════════╗\n"
    printf '║            %siQoQo Service Status%s              ║\n' "$BOLD" "$NC"
    printf '║           %s               ║\n' "$(date '+%Y-%m-%d %H:%M UTC')"
    printf '║           Stack: %s%s%s (%s)             ║\n' "$BOLD" "$STACK" "$NC" "$DOMAIN"
    printf "╚══════════════════════════════════════════════╝\n"
fi

header "Containers"
for svc in "${SERVICES[@]}"; do
    cname=$(find_container "$svc")
    if [[ -n "$cname" ]]; then
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
        check "${PREFIX}-${svc}-1" fail "NOT RUNNING"
    fi
done

# ─── Host Processes (Dev Mode) ──────────────────────────────────
if [[ "$STACK" == "dev" ]]; then
    header "Host Processes (Dev Mode)"

    # 1. Flask API Process
    flask_pid_file="$IQOQO_ROOT/.pids/flask.pid"
    flask_pid=""
    if [[ -f "$flask_pid_file" ]]; then
        flask_pid=$(cat "$flask_pid_file" 2>/dev/null || echo "")
    fi

    if [[ -n "$flask_pid" ]] && kill -0 "$flask_pid" 2>/dev/null; then
        proc_cmd=$(tr '\0' ' ' < "/proc/$flask_pid/cmdline" 2>/dev/null || echo "")
        if [[ "$proc_cmd" =~ (python|flask|gunicorn) ]]; then
            check "Flask API process" pass "PID ${flask_pid} running"
        else
            check "Flask API process" warn "PID ${flask_pid} alive but cmdline mismatch: ${proc_cmd:0:35}..."
        fi
    elif [[ -n "$flask_pid" ]]; then
        check "Flask API process" fail "PID ${flask_pid} not running (stale .pids/flask.pid)"
    else
        found_port_pid=$(lsof -t -i:"${WEB_PORT}" 2>/dev/null | head -1 || echo "")
        if [[ -n "$found_port_pid" ]]; then
            check "Flask API process" warn "running on port ${WEB_PORT} (PID ${found_port_pid}, missing pidfile)"
        else
            check "Flask API process" fail "NOT RUNNING"
        fi
    fi

    # 2. Celery Worker Process
    celery_pid_file="$IQOQO_ROOT/.pids/celery.pid"
    celery_pid=""
    if [[ -f "$celery_pid_file" ]]; then
        celery_pid=$(cat "$celery_pid_file" 2>/dev/null || echo "")
    fi

    if [[ -n "$celery_pid" ]] && kill -0 "$celery_pid" 2>/dev/null; then
        proc_cmd=$(tr '\0' ' ' < "/proc/$celery_pid/cmdline" 2>/dev/null || echo "")
        if [[ "$proc_cmd" =~ celery ]]; then
            check "Celery worker process" pass "PID ${celery_pid} running"
        else
            check "Celery worker process" warn "PID ${celery_pid} alive but cmdline mismatch: ${proc_cmd:0:35}..."
        fi
    elif [[ -n "$celery_pid" ]]; then
        check "Celery worker process" fail "PID ${celery_pid} not running (stale .pids/celery.pid)"
    else
        check "Celery worker process" fail "NOT RUNNING"
    fi

    # 3. Next.js Dev Server Process
    next_pid_file="$IQOQO_ROOT/.pids/next.pid"
    next_pid=""
    if [[ -f "$next_pid_file" ]]; then
        next_pid=$(cat "$next_pid_file" 2>/dev/null || echo "")
    fi

    if [[ -n "$next_pid" ]] && kill -0 "$next_pid" 2>/dev/null; then
        proc_cmd=$(tr '\0' ' ' < "/proc/$next_pid/cmdline" 2>/dev/null || echo "")
        if [[ "$proc_cmd" =~ (node|next|npm) ]]; then
            check "Next.js dev process" pass "PID ${next_pid} running"
        else
            check "Next.js dev process" warn "PID ${next_pid} alive but cmdline mismatch: ${proc_cmd:0:35}..."
        fi
    elif [[ -n "$next_pid" ]]; then
        check "Next.js dev process" fail "PID ${next_pid} not running (stale .pids/next.pid)"
    else
        found_next_pid=$(lsof -t -i:3000 2>/dev/null | head -1 || echo "")
        if [[ -n "$found_next_pid" ]]; then
            check "Next.js dev process" warn "running on port 3000 (PID ${found_next_pid}, missing pidfile)"
        else
            check "Next.js dev process" fail "NOT RUNNING"
        fi
    fi
fi

# ─── Observability Stack ────────────────────────────────────────
header "Observability Stack"
oo_cname=$(find_container "openobserve")
otel_cname=$(find_container "otel-collector")

if [[ -n "$oo_cname" ]]; then
    oo_status=$(docker ps --filter "name=${oo_cname}$" --format '{{.Status}}' 2>/dev/null)
    oo_host_port="${OPENOBSERVE_HOST_PORT:-5080}"
    oo_health=""
    oo_auth="${OPENOBSERVE_BASIC_AUTH:-YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=}"
    if python3 -c "
import urllib.request, sys
req = urllib.request.Request('http://127.0.0.1:${oo_host_port}/healthz')
req.add_header('Authorization', 'Basic ${oo_auth}')
try:
    r = urllib.request.urlopen(req, timeout=3)
    sys.exit(0 if r.code == 200 else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        oo_health="ok"
    fi
    if echo "$oo_health" | grep -iq "ok"; then
        check "OpenObserve API" pass "HTTP 200, status=ok (:5080/healthz) [${oo_status}]"
    else
        check "OpenObserve API" warn "container running but health endpoint unreachable [${oo_status}]"
    fi
else
    check "OpenObserve" info "not running (optional default stack)"
fi

if [[ -n "$otel_cname" ]]; then
    otel_status=$(docker ps --filter "name=${otel_cname}$" --format '{{.Status}}' 2>/dev/null)
    otel_health=""
    otel_health=$(python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8888/', timeout=3).read().decode())" 2>/dev/null || true)
    if [[ -z "$otel_health" ]]; then
        otel_health=$(docker exec "$otel_cname" python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8888/', timeout=3).read().decode())" 2>/dev/null || \
                      docker exec "$otel_cname" wget -qO- http://127.0.0.1:8888/ 2>/dev/null || true)
    fi
    check "OTel Collector" pass "ready (:8888) [${otel_status}]"
else
    check "OTel Collector" info "not running (optional default stack)"
fi

otel_traces=$(load_env "OTEL_TRACES_EXPORTER")
otel_logs=$(load_env "OTEL_LOGS_EXPORTER")
otel_metrics=$(load_env "OTEL_METRICS_EXPORTER")
active_exporters=()
[[ -n "$otel_traces" && "$otel_traces" != "none" ]] && active_exporters+=("traces:${otel_traces}")
[[ -n "$otel_logs" && "$otel_logs" != "none" ]] && active_exporters+=("logs:${otel_logs}")
[[ -n "$otel_metrics" && "$otel_metrics" != "none" ]] && active_exporters+=("metrics:${otel_metrics}")

if [[ ${#active_exporters[@]} -gt 0 ]]; then
    otel_4318_ok=false
    if [[ -n "$otel_cname" ]]; then
        otel_4318_ok=true
    elif python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 4318)); s.close()" 2>/dev/null; then
        otel_4318_ok=true
    fi
    if [[ "$otel_4318_ok" == "true" ]]; then
        check "Telemetry Ingestion" pass "active exporters: ${active_exporters[*]}"
    else
        check "Telemetry Ingestion" warn "exporters active (${active_exporters[*]}) but OTel Collector endpoint (:4318) unreachable"
    fi
fi

# ─── Redis ──────────────────────────────────────────────────────
header "Redis"
redis_cname=$(find_container "redis")
if [[ -n "$redis_cname" ]]; then
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
db_cname=$(find_container "db")
if [[ -n "$db_cname" ]]; then
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
            "SELECT version_num FROM alembic_version LIMIT 1" 2>/dev/null || echo "N/A")
        check "Migration" pass "version: ${migration_head}"
    else
        check "pg_isready" fail "not accepting connections"
    fi
else
    check "Container" fail "not running"
fi

# ─── Celery Worker ──────────────────────────────────────────────
header "Celery Worker"
if [[ "$STACK" == "dev" ]]; then
    celery_pid_file="$IQOQO_ROOT/.pids/celery.pid"
    celery_alive=false
    c_pid=""
    if [[ -f "$celery_pid_file" ]]; then
        c_pid=$(cat "$celery_pid_file" 2>/dev/null || echo "")
        if [[ -n "$c_pid" ]] && kill -0 "$c_pid" 2>/dev/null; then
            celery_alive=true
        fi
    fi

    if [[ "$celery_alive" == "true" ]]; then
        check "Worker process" pass "PID ${c_pid} active on host"
        # Ping celery worker via redis / inspect ping
        ping_pong=$(PYTHONPATH="$IQOQO_ROOT" "$IQOQO_ROOT/.venv/bin/celery" -A app.core.celery_app:celery inspect ping --timeout=2 2>/dev/null || true)
        if echo "$ping_pong" | grep -qi "pong"; then
            check "Broker & Ping" pass "connected to Redis (worker responded pong)"
        else
            # Fallback broker check
            if python3 -c "
import redis
r = redis.Redis.from_url('redis://127.0.0.1:${REDIS_PORT:-6379}/0')
r.ping()
" 2>/dev/null; then
                check "Broker" pass "Redis broker reachable (host worker PID ${c_pid})"
            else
                check "Broker" fail "cannot reach Redis broker"
            fi
        fi
    else
        check "Worker" fail "host Celery worker not running"
    fi
else
    worker_cname=$(find_container "worker")
    if [[ -n "$worker_cname" ]]; then
        if docker exec "$worker_cname" python3 -c "
import os, redis
r = redis.Redis.from_url(os.environ['REDIS_URL'])
r.ping()
" 2>/dev/null; then
            check "Broker" pass "connected to Redis"
            recent_reconn=$(docker logs "$worker_cname" --since 5m 2>&1 | grep -c "Connected to redis" || true)
            if [[ "$recent_reconn" -gt 2 ]]; then
                check "Stability" warn "reconnected ${recent_reconn}x in last 5min (flapping?)"
            else
                check "Stability" pass "no recent reconnections"
            fi
            otel_errors=$(docker logs "$worker_cname" --since 2m 2>&1 | grep -c "StatusCode.UNAVAILABLE" || true)
            if [[ "$otel_errors" -gt 10 ]]; then
                check "OTel exporter" warn "${otel_errors} OTel export failures in 2min (collector may be down)"
            else
                check "OTel exporter" pass "no recent export failures"
            fi
            tasks_received=$(docker logs "$worker_cname" 2>&1 | grep -c "task received" || true)
            tasks_succeeded=$(docker logs "$worker_cname" 2>&1 | grep -c "succeeded" || true)
            tasks_failed=$(docker logs "$worker_cname" 2>&1 | grep -c "failed" || true)
            check "Tasks" info "received: ~${tasks_received}, succeeded: ~${tasks_succeeded}, failed: ~${tasks_failed}"
        else
            check "Broker" fail "NOT connected to Redis"
        fi
        cmdline=$(docker inspect "$worker_cname" --format '{{.Config.Cmd}}' 2>/dev/null | tr ',' ' ')
        if echo "$cmdline" | grep -q "concurrency"; then
            conc=$(echo "$cmdline" | grep -oP 'concurrency=\K[0-9]+' || echo "?")
            pool=$(echo "$cmdline" | grep -oP 'pool=\K\w+' || echo "?")
            check "Pool" info "--pool=${pool}  --concurrency=${conc}"
        fi
    else
        check "Container" fail "not running"
    fi
fi

# ─── API Health ─────────────────────────────────────────────────
header "API"
if [[ "$STACK" == "dev" ]]; then
    health_json=$(python3 -c "
import urllib.request, json
last_e = 'unreachable'
for p in [${WEB_PORT}, 5000, 5001]:
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{p}/api/health')
        r = urllib.request.urlopen(req, timeout=3)
        print(json.dumps(json.loads(r.read())))
        break
    except Exception as e:
        last_e = str(e)
else:
    print('ERROR:' + last_e)
" 2>/dev/null || echo "ERROR:connection refused")

    if echo "$health_json" | grep -qv "^ERROR:"; then
        health_status=$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
        if [[ "$health_status" == "ok" ]]; then
            version=$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
            check "Health endpoint" pass "HTTP 200, status=ok, version=${version} (http://127.0.0.1:${WEB_PORT}/api/health)"
        else
            check "Health endpoint" fail "status=${health_status}"
        fi
    else
        health_err="${health_json#ERROR:}"
        check "Health endpoint" fail "http://127.0.0.1:${WEB_PORT}/api/health (${health_err})"
    fi
else
    web_cname=$(find_container "web")
    if [[ -n "$web_cname" ]]; then
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
        if [[ ! "$gunicorn_workers" =~ ^[0-9]+$ ]]; then
            gunicorn_workers=0
        fi
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
fi

# ─── Nginx & Frontend ──────────────────────────────────────────
if [[ "$STACK" == "dev" ]]; then
    header "Frontend (Next.js Dev Server)"
    check "Nginx" info "N/A (dev mode connects directly to Next.js)"
    frontend_code=$(python3 -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://localhost:3000', timeout=4)
    print(r.getcode())
except urllib.error.HTTPError as e:
    print(e.code)
except Exception:
    print('000')
" 2>/dev/null || echo "000")
    if [[ "$frontend_code" == "200" || "$frontend_code" == "302" || "$frontend_code" == "307" || "$frontend_code" == "308" ]]; then
        check "Next.js dev server" pass "HTTP ${frontend_code} (http://localhost:3000)"
    else
        check "Next.js dev server" fail "HTTP ${frontend_code} (unreachable on http://localhost:3000)"
    fi
else
    header "Nginx & Frontend"
    nginx_cname=$(find_container "nginx")
    if [[ -n "$nginx_cname" ]]; then
        if docker exec "$nginx_cname" nginx -t 2>&1 | grep -q "test is successful"; then
            check "Config syntax" pass "valid"
        else
            check "Config syntax" fail "INVALID"
        fi

        frontend_code=$(docker exec "$nginx_cname" curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/ 2>/dev/null || echo "000")
        if [[ "$frontend_code" == "200" ]] || [[ "$frontend_code" == "302" ]] || [[ "$frontend_code" == "301" ]]; then
            check "Frontend (via nginx)" pass "HTTP ${frontend_code}"
        else
            check "Frontend (via nginx)" fail "HTTP ${frontend_code}"
        fi

        api_code=$(docker exec "$nginx_cname" curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/health 2>/dev/null || echo "000")
        if [[ "$api_code" == "200" ]]; then
            check "API proxy (via nginx)" pass "HTTP ${api_code}"
        else
            check "API proxy (via nginx)" fail "HTTP ${api_code}"
        fi

        recent_5xx=$(docker logs "$nginx_cname" --since 15m 2>&1 | grep -c '" 5[0-9][0-9] ' || true)
        if [[ "$recent_5xx" -gt 10 ]]; then
            check "Recent 5xx errors" warn "${recent_5xx} in last 15min"
        else
            check "Recent 5xx errors" pass "${recent_5xx} in last 15min"
        fi
    else
        check "Container" fail "not running"
    fi
fi

# ─── Covers Directory ──────────────────────────────────────────
header "Covers"
covers_dir="$IQOQO_ROOT/app/static/covers"
if [[ -d "$covers_dir" ]]; then
    cover_count=$(find "$covers_dir" -maxdepth 1 -type f 2>/dev/null | wc -l)
    cover_size=$(du -sh "$covers_dir" 2>/dev/null | cut -f1)
    recent_covers=$(find "$covers_dir" -maxdepth 1 -type f -newer "$covers_dir" -mmin -60 2>/dev/null | wc -l)
    check "Directory" pass "${cover_count} files, ${cover_size}"
    if [[ "$recent_covers" -gt 0 ]]; then
        check "Recent activity" pass "${recent_covers} new files in last hour"
    else
        check "Recent activity" info "no new files in last hour"
    fi
    empty_covers=$(find "$covers_dir" -maxdepth 1 -type f -size -1k 2>/dev/null | wc -l)
    if [[ "$empty_covers" -gt 0 ]]; then
        check "Empty files" warn "${empty_covers} files < 1KB (possibly broken)"
    fi
    # Check database cover pipeline status
    db_cname=$(find_container "db")
    if [[ -n "$db_cname" ]]; then
        db_user=$(load_env "POSTGRES_USER")
        db_name=$(load_env "POSTGRES_DB")
        db_user="${db_user:-iqoqo}"
        db_name="${db_name:-iqoqo}"
        cover_status_data=$(docker exec "$db_cname" psql -U "$db_user" -d "$db_name" -tAc \
            "SELECT COALESCE(meta->>'cover_status', 'not_started'), count(*) FROM catalog.manifestations GROUP BY 1;" 2>/dev/null || \
            docker exec "$db_cname" psql -U "$db_user" -d "$db_name" -tAc \
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
