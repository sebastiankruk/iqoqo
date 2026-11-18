# Why

Production incident analysis (`🪳 OpenObserve Telemetry Blackout — Credential Rot & Broken RUM Chain.md`) revealed a 62-hour total telemetry blackout on `iqoqo.kruk.cc` during which **49,320 signals** (logs, traces, and metrics) were permanently dropped while `make status prod` reported every observability check as green (`✓`):

1. **Defect D1 — `.env` Credential Regeneration vs. Volume-Frozen OpenObserve Root User (`scripts/ensure_env_secrets.py`, `Makefile`)**:
   - OpenObserve (`v0.91.5`) seeds `ZO_ROOT_USER_EMAIL` and `ZO_ROOT_USER_PASSWORD` into `/data/db` inside the persistent `openobserve_data` volume **only on first boot**.
   - When `.env` is regenerated or reconciled across environments (`scripts/ensure_env_secrets.py`), `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH` are updated in `.env` and `InstanceSettings`, while the existing `openobserve_data` volume continues enforcing the original root user/password. Furthermore, quoted `.env` values could be read without quote stripping. Every OTel Collector export then fails with `HTTP Status Code 401: Unauthenticated` until the volume's `/data/db` auth store is reset or `.env` is restored.
2. **Defect D2 — `make status` Blind to Collector $\to$ OpenObserve `401` Failures (`scripts/iqoqo-status.sh`)**:
   - `scripts/iqoqo-status.sh` (lines 417–472) only probes OpenObserve's unauthenticated `GET /healthz` endpoint (which returns `200 {"status":"ok"}` even with an invalid `Authorization` header!), checks `:8888/` on `otel-collector`, and checks whether port `:4318` accepts TCP connections. It never performs an authenticated OpenObserve API call or checks `otel-collector` logs for `Exporting failed` / `401` errors—reporting 100% green during a total telemetry blackout.
3. **Defect D3 — Containerized Browser OTel Trace (`/v1/traces`) & RUM (`/rum/*`) Loopback Blackhole (`frontend/next.config.ts`, `docker-compose.yml`, `deploy/nginx.conf*`)**:
   - `BrowserTelemetry` (`frontend/components/browser-telemetry.tsx:76`) posts browser Web Vitals spans to `window.location.origin + "/v1/traces"` when `NEXT_PUBLIC_OTEL_COLLECTOR_URL` is unset.
   - `frontend/next.config.ts` (lines 143–144) hardcodes the `/v1/traces` rewrite destination to `http://127.0.0.1:4318/v1/traces` and `/rum/:path*` to `http://127.0.0.1:5080/rum/:path*`. Inside the `frontend` Docker container, `127.0.0.1` is the frontend container's own loopback interface—not the `otel-collector` or `openobserve` container! Every browser `POST /v1/traces` request routed to Next.js fails with `HTTP 500 Internal Server Error` (`ECONNREFUSED 127.0.0.1:4318`).

## What Changes

- **Credential Drift Detection, Quote Sanitization & Non-Destructive Auth Reset (`scripts/ensure_env_secrets.py`, `Makefile`)**:
  - Strip surrounding single/double quotes when reading or deriving `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH` in `scripts/ensure_env_secrets.py`.
  - Add a live OpenObserve authentication probe (`probe_openobserve_auth()`) in `scripts/ensure_env_secrets.py` that tests `OPENOBSERVE_BASIC_AUTH` against a running local OpenObserve instance (`GET /api/default/rumtoken` or `POST /api/default/_search`). If OpenObserve is reachable on `:5080` and returns `401`/`403`, emit a loud warning explaining that the `openobserve_data` volume's `/data/db` has frozen an older credential and instructing the operator to run `make monitoring-reset-auth`.
  - Add a `monitoring-reset-auth` target in `Makefile` that stops `openobserve`, backs up and clears `/data/db` (the user/org metadata store) inside the `openobserve_data` volume while **preserving `/data/stream` historical parquet telemetry**, restarts `openobserve` + `otel-collector` so OpenObserve re-seeds the root user from current `.env`, and re-provisions the RUM token (`scripts/provision_rum_token.py`).
- **End-to-End Authenticated Telemetry Verification in `make status` (`scripts/iqoqo-status.sh`)**:
  - Strip surrounding quotes from `oo_auth` when loaded from `.env`.
  - Follow the `/healthz` check with an authenticated `POST http://127.0.0.1:${oo_host_port}/api/default/_search` probe using `Authorization: Basic ${oo_auth}`. Report `fail` if HTTP `401`/`403` is returned (`credential mismatch with openobserve_data volume — run 'make monitoring-reset-auth'`).
  - Inspect `otel-collector` container logs over the last 5 minutes (`docker logs "$otel_cname" --since 5m`) for `Exporting failed` / `Status Code 401` / `dropping data` and report `fail` or `warn` when export errors are occurring.
- **Container-Aware `/v1/traces` & `/rum/*` Routing (`frontend/next.config.ts`, `docker-compose.yml`, `deploy/nginx.conf`, `deploy/nginx.conf.example`, `scripts/validate_nginx_example.py`)**:
  - In `frontend/next.config.ts`, resolve the `/v1/traces` rewrite target from `process.env.OTEL_COLLECTOR_HTTP_URL || process.env.OTEL_EXPORTER_OTLP_ENDPOINT || "http://127.0.0.1:4318"` and the `/rum/:path*` rewrite target from `process.env.OPENOBSERVE_INTERNAL_URL || "http://127.0.0.1:5080"`.
  - In `docker-compose.yml`, pass `OPENOBSERVE_INTERNAL_URL=${OPENOBSERVE_INTERNAL_URL:-http://openobserve:5080}` to the `frontend` service environment (alongside existing `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`).
  - In `deploy/nginx.conf` and `deploy/nginx.conf.example`, add an `iqoqo_otel_collector` upstream (`otel-collector:4318` / `${OTEL_COLLECTOR_UPSTREAM}:${OTEL_COLLECTOR_PORT}`) and a rate-limited `location = /v1/traces` block proxying browser OTLP trace beacons directly to `http://iqoqo_otel_collector/v1/traces` without buffering.

## Capabilities

### New Capabilities
- `openobserve-telemetry-and-rum-resilience`: OpenObserve credential drift detection and `/data/db` auth reset preserving parquet streams, authenticated `make status` pipeline verification, and container-safe `/v1/traces` & `/rum/*` routing across Next.js and Nginx.

### Modified Capabilities
- None.

## Impact

- **Scripts & Makefile (`scripts/ensure_env_secrets.py`, `scripts/iqoqo-status.sh`, `Makefile`)**: Prevents silent `401` telemetry blackouts, detects credential drift immediately in `make status`, and provides a 1-command `make monitoring-reset-auth` recovery target that preserves `/data/stream` data.
- **Frontend & Edge Proxy (`frontend/next.config.ts`, `docker-compose.yml`, `deploy/nginx.conf`, `deploy/nginx.conf.example`, `scripts/validate_nginx_example.py`)**: Restores browser Web Vitals (`/v1/traces`) and OpenObserve RUM (`/rum/*`) ingestion in containerized deployments.
- **Tests**: Unit and script tests in `tests/test_scripts.py`, `tests/test_infra_config.py`, and `tests/bash/`.
