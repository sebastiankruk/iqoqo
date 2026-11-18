## 1. OpenObserve Credential Quote Sanitization, Drift Probe & Auth Reset (`D1`)

- [x] 1.1 In `scripts/ensure_env_secrets.py`, strip surrounding quotes on `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH`, and implement `probe_openobserve_auth()` to detect HTTP `401`/`403` credential drift against a running local OpenObserve instance and print an actionable warning pointing to `make monitoring-reset-auth`.
- [x] 1.2 In `Makefile`, add `monitoring-reset-auth` (and declare it in `.PHONY`) to safely back up and reset `/data/db` inside the OpenObserve volume while preserving `/data/stream` parquet telemetry, restart `openobserve` and `otel-collector`, and re-run `scripts/provision_rum_token.py`.

## 2. Authenticated OpenObserve & Collector Pipeline Verification in `make status` (`D2`)

- [x] 2.1 In `scripts/iqoqo-status.sh`, strip surrounding quotes from `oo_auth`, add an authenticated `POST /api/default/_search` check that reports `fail` on HTTP `401`/`403`, and inspect `otel-collector` logs (`--since 5m`) for `Exporting failed` / `401` errors so telemetry blackouts are immediately flagged.

## 3. Containerized Browser OTel Trace (`/v1/traces`) & RUM (`/rum/*`) Routing (`D3`)

- [x] 3.1 In `frontend/next.config.ts` and `docker-compose.yml`, resolve `/v1/traces` and `/rum/:path*` rewrite targets from `OTEL_COLLECTOR_HTTP_URL` / `OTEL_EXPORTER_OTLP_ENDPOINT` and `OPENOBSERVE_INTERNAL_URL` (defaulting to `http://127.0.0.1:4318` and `http://127.0.0.1:5080` in host dev mode, and `http://otel-collector:4318` / `http://openobserve:5080` in Docker).
- [x] 3.2 In `deploy/nginx.conf`, `deploy/nginx.conf.example`, and `scripts/validate_nginx_example.py`, add the `iqoqo_otel_collector` upstream and rate-limited `location = /v1/traces` proxy block so edge and container Nginx proxies forward browser OTLP trace beacons directly to `otel-collector:4318`.

## 4. Regression Tests & Verification

- [x] 4.1 Add unit and config tests in `tests/test_scripts.py`, `tests/test_infra_config.py`, and `tests/bash/` covering `ensure_env_secrets.py` quote stripping and `probe_openobserve_auth()`, `iqoqo-status.sh` authenticated `/api/default/_search` failure detection, `next.config.ts` dynamic rewrite URLs, and Nginx `/v1/traces` validation.
