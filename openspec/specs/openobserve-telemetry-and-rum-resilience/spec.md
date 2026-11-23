# openobserve-telemetry-and-rum-resilience Specification

## Purpose

Define OpenObserve credential hygiene and drift detection, authenticated observability verification in `make status`, and container-aware proxy routing for browser OTel traces and RUM telemetry.

## Requirements

### Requirement: OpenObserve Credential Quote Sanitization, Drift Detection, and Non-Destructive Auth Reset

`scripts/ensure_env_secrets.py` MUST strip surrounding quotes when parsing `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH` from `.env`, and MUST probe a running local OpenObserve instance using `OPENOBSERVE_BASIC_AUTH` to detect credential drift against the persistent `openobserve_data` volume. Additionally, `Makefile` SHALL provide a `monitoring-reset-auth` target that enforces `--enforce-openobserve-password-policy` and `0600` permissions on the active env file (`--project-directory $(DEPLOY_DIR)` for `preview`), resets OpenObserve's `/data/db` metadata store while preserving `/data/stream` parquet telemetry files, recreates `openobserve`, `otel-collector`, `web`, `worker`, and `frontend` via `docker compose ... up -d --force-recreate --no-deps` so updated environment variables take effect, syncs rotated `OPENOBSERVE_BASIC_AUTH` into `InstanceSettings`, and re-provisions the RUM token by capturing `provision_rum_token.py` stdout cleanly without leaking `RUM_CLIENT_TOKEN` to terminal output.

#### Scenario: Quote-wrapped OpenObserve credentials in .env produce clean Basic Auth token

- **GIVEN** `.env` contains `OPENOBSERVE_ROOT_USER="admin@iqoqo.local"` or `OPENOBSERVE_ROOT_PASSWORD="secret"` with surrounding quotes
- **WHEN** `ensure_env_secrets()` computes `OPENOBSERVE_BASIC_AUTH`
- **THEN** the quotes are stripped before Base64 encoding and before writing `OPENOBSERVE_BASIC_AUTH`

#### Scenario: Running OpenObserve with drifted volume credentials emits actionable warning

- **GIVEN** OpenObserve is reachable on `OPENOBSERVE_HOST_PORT` (`5080`) and rejects `OPENOBSERVE_BASIC_AUTH` with HTTP `401` or `403`
- **WHEN** `probe_openobserve_auth()` runs during secret verification
- **THEN** it logs a warning identifying the credential mismatch between `.env` and the `openobserve_data` volume and points the operator to `make monitoring-reset-auth`

#### Scenario: monitoring-reset-auth recreates containers and injects RUM token without stdout leakage

- **GIVEN** OpenObserve has drifted `/data/db` credentials in `openobserve_data` and `make monitoring-reset-auth MODE=preview DEPLOY_DIR=/opt/pre.iqoqo` runs
- **WHEN** `/data/db` is cleared and OpenObserve credentials are regenerated
- **THEN** `openobserve` and `otel-collector` MUST be recreated with `docker compose --project-directory $(DEPLOY_DIR) ... up -d --force-recreate --no-deps` (not `docker start` / `docker restart`), `provision_rum_token.py` stdout MUST be captured rather than printed to stdout (`RUM_CLIENT_TOKEN=` MUST NOT appear in terminal output), and `frontend` MUST be force-recreated with the exported `OPENOBSERVE_RUM_*` environment variables.

#### Scenario: monitoring-reset-auth syncs rotated OPENOBSERVE_BASIC_AUTH into InstanceSettings

- **GIVEN** `monitoring-reset-auth` rotates `OPENOBSERVE_ROOT_PASSWORD` and `OPENOBSERVE_BASIC_AUTH` in `$DEPLOY_ENV_FILE` while `web` and `db` are running
- **WHEN** `monitoring-reset-auth` completes
- **THEN** `OPENOBSERVE_BASIC_AUTH` MUST be synced into encrypted `InstanceSettings` and `web` / `worker` MUST be force-recreated so their process environments reflect the updated credentials.

### Requirement: End-to-End Authenticated OpenObserve and OTel Collector Verification in `make status`

`scripts/iqoqo-status.sh` MUST verify OpenObserve authentication using an authenticated API endpoint (`POST /api/default/_search`) in addition to `/healthz`, MUST resolve DB-stored `OPENOBSERVE_BASIC_AUTH` via `docker exec "$web_cname"` (using `/usr/src/app`) on non-dev stacks rather than host `python3`, MUST inspect `otel-collector` container logs for recent export failures (`Exporting failed` or `401`), and MUST report `Browser RUM` readiness from the running `frontend` container (surfacing a warning when an `https://` origin and running OpenObserve exist without a provisioned `OPENOBSERVE_RUM_CLIENT_TOKEN`, unless `OTEL_TRACES_EXPORTER=none`). Furthermore, `Makefile` `status` MUST pass `--deploy-dir $(DEPLOY_DIR)` for `preview` stacks in both its local-script and container-extracted fallback branches.

#### Scenario: Invalid OPENOBSERVE_BASIC_AUTH is flagged as FAIL by make status

- **GIVEN** the `openobserve` container is running and `/healthz` returns `200`, but `POST /api/default/_search` with `Authorization: Basic ${oo_auth}` returns HTTP `401` or `403`
- **WHEN** `scripts/iqoqo-status.sh` evaluates the Observability Stack
- **THEN** it records a `fail` check for OpenObserve Authentication rather than passing on unauthenticated `/healthz` alone

#### Scenario: OTel Collector export failures in recent logs are surfaced by make status

- **GIVEN** the `otel-collector` container is running and its recent logs (`--since 5m`) contain `Exporting failed`
- **WHEN** `scripts/iqoqo-status.sh` evaluates the OTel Collector
- **THEN** it reports a `warn` or `fail` check indicating telemetry export errors

#### Scenario: Preview status resolves DB-stored OPENOBSERVE_BASIC_AUTH via web container

- **GIVEN** `OPENOBSERVE_BASIC_AUTH` is absent from `$DEPLOY_DIR/.env` and stored only in `InstanceSettings` on a `preview` stack where host `python3` has no repo/DB access
- **WHEN** `scripts/iqoqo-status.sh --stack preview --deploy-dir /opt/pre.iqoqo` runs
- **THEN** it MUST retrieve `OPENOBSERVE_BASIC_AUTH` via `docker exec "$web_cname"` using `/usr/src/app` and authenticate against `POST /api/default/_search` without printing the token value.

#### Scenario: Makefile status fallback branch preserves --deploy-dir for preview

- **GIVEN** `make status STACK=preview DEPLOY_DIR=/opt/pre.iqoqo` runs in a deploy directory without a local `scripts/iqoqo-status.sh`
- **WHEN** the fallback branch extracts `scripts/iqoqo-status.sh` from the `web` container or image
- **THEN** it MUST invoke the extracted script with `--stack preview --deploy-dir /opt/pre.iqoqo`.

#### Scenario: Status reports Browser RUM readiness and flags missing token on HTTPS preview with OpenObserve

- **GIVEN** a `preview` stack with `NEXT_PUBLIC_FRONTEND_URL=https://preview.iqoqo.cc`, a running `openobserve` container, `OTEL_TRACES_EXPORTER` not equal to `none`, and an empty `OPENOBSERVE_RUM_CLIENT_TOKEN` in `frontend`
- **WHEN** `scripts/iqoqo-status.sh` evaluates Browser RUM
- **THEN** it MUST surface a warning rather than silently passing so missing RUM provisioning is actionable.

### Requirement: Container-Aware Browser OTel Trace (`/v1/traces`) and RUM (`/rum/*`) Proxy Routing
`frontend/next.config.ts` MUST resolve the `/v1/traces` and `/rum/:path*` rewrite destinations from environment variables (`OTEL_COLLECTOR_HTTP_URL` / `OTEL_EXPORTER_OTLP_ENDPOINT` and `OPENOBSERVE_INTERNAL_URL`, falling back to `http://127.0.0.1:4318` and `http://127.0.0.1:5080` for host-native dev mode) rather than hardcoding `127.0.0.1`. Furthermore, `deploy/nginx.conf` and `deploy/nginx.conf.example` MUST proxy `/v1/traces` to the `otel-collector` HTTP receiver (`:4318`) with rate limiting and unbuffered request forwarding.

#### Scenario: Containerized Next.js rewrites /v1/traces and /rum/:path* to Docker service hostnames

- **GIVEN** `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318` and `OPENOBSERVE_INTERNAL_URL=http://openobserve:5080` are set in the `frontend` container environment
- **WHEN** `next.config.ts` builds its `rewrites()` rules
- **THEN** `/v1/traces` rewrites to `http://otel-collector:4318/v1/traces` and `/rum/:path*` rewrites to `http://openobserve:5080/rum/:path*`

#### Scenario: Edge and container Nginx configs proxy /v1/traces to the OTel Collector

- **GIVEN** a browser client posts OTLP JSON trace spans to `/v1/traces` through Nginx
- **WHEN** Nginx matches `location = /v1/traces` in `deploy/nginx.conf` or `deploy/nginx.conf.example`
- **THEN** the request is rate-limited via `zone=api_rum` and proxied directly to the `iqoqo_otel_collector` upstream (`otel-collector:4318`)
