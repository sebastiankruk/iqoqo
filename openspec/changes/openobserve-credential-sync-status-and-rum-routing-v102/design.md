## Context

Production incident analysis (`🪳 OpenObserve Telemetry Blackout — Credential Rot & Broken RUM Chain.md`) identified three architectural blind spots in the OpenObserve + OpenTelemetry observability stack on `iqoqo.kruk.cc`:

1. **Frozen Volume Root User vs. `.env` Secret Sync (`D1`)**: OpenObserve `v0.91.5` reads `ZO_ROOT_USER_EMAIL` and `ZO_ROOT_USER_PASSWORD` only when initializing an empty `/data/db` directory inside `openobserve_data`. Subsequent changes to `.env` (or regeneration by `scripts/ensure_env_secrets.py`) update `OPENOBSERVE_BASIC_AUTH` passed to `otel-collector`, causing every OTLP export to fail with `401 Unauthenticated`.
2. **Unauthenticated Health Probe in `make status` (`D2`)**: `scripts/iqoqo-status.sh` sends `Authorization: Basic ${oo_auth}` to `GET /healthz`, an endpoint that does not check authentication and always returns `200 {"status":"ok"}`. Furthermore, `scripts/iqoqo-status.sh` never checks `otel-collector` logs for `Exporting failed` or `401` responses.
3. **Loopback `127.0.0.1` Rewrite Inside `frontend` Container (`D3`)**: `frontend/next.config.ts` hardcodes `http://127.0.0.1:4318/v1/traces` and `http://127.0.0.1:5080/rum/:path*`. In Docker Compose, `127.0.0.1` inside `iqoqo-frontend-1` is the frontend container's own loopback interface, so every `POST /v1/traces` request that reaches Next.js fails with `HTTP 500` (`ECONNREFUSED`).

## Goals / Non-Goals

**Goals:**
- Sanitize quotes on OpenObserve credentials in `scripts/ensure_env_secrets.py` and detect `401`/`403` drift against running OpenObserve instances.
- Provide `make monitoring-reset-auth [preview|prod]` to safely reset OpenObserve's `/data/db` auth store while preserving `/data/stream` parquet telemetry and re-provisioning the RUM token.
- Upgrade `scripts/iqoqo-status.sh` (`make status`) to verify authenticated OpenObserve search (`POST /api/default/_search`) and check `otel-collector` logs for export errors.
- Route `/v1/traces` and `/rum/:path*` to `otel-collector:4318` and `openobserve:5080` in Docker Compose and Nginx (`deploy/nginx.conf`, `deploy/nginx.conf.example`, `frontend/next.config.ts`).

**Non-Goals:**
- Replacing OpenObserve or the OpenTelemetry Collector with external SaaS telemetry vendors.

## Decisions

### Decision 1: Quote Sanitization, Live Auth Drift Probe & `make monitoring-reset-auth` (`scripts/ensure_env_secrets.py`, `Makefile`)
- **Choice**:
  - In `scripts/ensure_env_secrets.py`, strip surrounding matching `'` / `"` quotes when reading `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH`.
  - Add `probe_openobserve_auth(basic_auth: str, host_port: int = 5080) -> tuple[str, str]` in `scripts/ensure_env_secrets.py` (invoked when OpenObserve is reachable on `127.0.0.1:${OPENOBSERVE_HOST_PORT:-5080}`). It sends `POST /api/default/_search` with `{"query":{"sql":"SELECT 1","size":1}}` and `Authorization: Basic <basic_auth>`. If HTTP `401` or `403` is returned, `ensure_env_secrets.py` prints a clear `⚠️ WARNING: OpenObserve rejected OPENOBSERVE_BASIC_AUTH (HTTP 401/403). The openobserve_data volume (/data/db) is locked to an older password. Run 'make monitoring-reset-auth' to resync without losing /data/stream telemetry.`
  - In `Makefile`, add `monitoring-reset-auth`: stops `openobserve`, runs a one-shot alpine container mounting `${COMPOSE_PROJECT}_openobserve_data` at `/data` to move `/data/db` to `/data/db.bak.<timestamp>` (leaving `/data/stream` intact), restarts `openobserve` and `otel-collector`, and runs `scripts/provision_rum_token.py`.
- **Rationale**: Preserves historical parquet telemetry in `/data/stream` while giving operators a safe, deterministic 1-command recovery path whenever `.env` credentials rotate.

### Decision 2: Authenticated `/api/default/_search` Probe & Collector Log Check in `scripts/iqoqo-status.sh`
- **Choice**:
  - Strip surrounding quotes from `oo_auth` in `scripts/iqoqo-status.sh`.
  - After verifying `/healthz`, execute a `POST http://127.0.0.1:${oo_host_port}/api/default/_search` probe with `Authorization: Basic ${oo_auth}`.
    - `200`: `check "OpenObserve Auth" pass "authenticated SQL search ok (/api/default/_search)"`
    - `401` / `403`: `check "OpenObserve Auth" fail "HTTP ${oo_auth_code} Unauthenticated — .env OPENOBSERVE_BASIC_AUTH mismatches openobserve_data volume (run 'make monitoring-reset-auth')"`
  - On `otel-collector`, check `docker logs "$otel_cname" --since 5m 2>&1 | grep -c "Exporting failed" || true`: if $> 0$, emit `check "OTel Export Pipeline" fail "${otel_export_errs} export failures in last 5m (check collector logs)"`; otherwise `check "OTel Export Pipeline" pass "0 export errors in last 5m"`.

### Decision 3: Container-Aware `/v1/traces` & `/rum/*` Proxy Targets (`frontend/next.config.ts`, `docker-compose.yml`, `deploy/nginx.conf*`)
- **Choice**:
  - In `frontend/next.config.ts`, compute:
    - `const otelCollectorUrl = (process.env.OTEL_COLLECTOR_HTTP_URL || process.env.OTEL_EXPORTER_OTLP_ENDPOINT || "http://127.0.0.1:4318").replace(/\/+$/, "");`
    - `const openobserveUrl = (process.env.OPENOBSERVE_INTERNAL_URL || "http://127.0.0.1:5080").replace(/\/+$/, "");`
    and rewrite `/v1/traces` $\to$ `${otelCollectorUrl}/v1/traces` and `/rum/:path*` $\to$ `${openobserveUrl}/rum/:path*`.
  - In `docker-compose.yml`, add `- OPENOBSERVE_INTERNAL_URL=${OPENOBSERVE_INTERNAL_URL:-http://openobserve:5080}` to `frontend.environment`.
  - In `deploy/nginx.conf` and `deploy/nginx.conf.example`, declare `upstream iqoqo_otel_collector` (`otel-collector:4318` / `${OTEL_COLLECTOR_UPSTREAM}:${OTEL_COLLECTOR_PORT}`) and `location = /v1/traces` proxying directly to `http://iqoqo_otel_collector` with `limit_req zone=api_rum burst=20 nodelay;`, and update `scripts/validate_nginx_example.py` placeholder map for `${OTEL_COLLECTOR_UPSTREAM}` and `${OTEL_COLLECTOR_PORT}`.

## Risks / Trade-offs

- **Risk**: `scripts/validate_nginx_example.py` validates every `${...}` placeholder in `deploy/nginx.conf.example` and runs `nginx -t`.
  - **Mitigation**: Register `OTEL_COLLECTOR_UPSTREAM` and `OTEL_COLLECTOR_PORT` in `scripts/validate_nginx_example.py` and run `IQOQO_AI_MODE=1 make validate-nginx` and `pytest tests/test_scripts.py`.
