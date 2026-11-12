# openobserve-telemetry-and-rum-resilience Specification

## Purpose

Define OpenObserve credential hygiene and drift detection, authenticated observability verification in `make status`, and container-aware proxy routing for browser OTel traces and RUM telemetry.

## Requirements

### Requirement: OpenObserve Credential Quote Sanitization, Drift Detection, and Non-Destructive Auth Reset
`scripts/ensure_env_secrets.py` MUST strip surrounding quotes when parsing `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH` from `.env`, and MUST probe a running local OpenObserve instance using `OPENOBSERVE_BASIC_AUTH` to detect credential drift against the persistent `openobserve_data` volume. Additionally, `Makefile` SHALL provide a `monitoring-reset-auth` target that resets OpenObserve's `/data/db` metadata store while preserving `/data/stream` parquet telemetry files and re-provisions the RUM token.

#### Scenario: Quote-wrapped OpenObserve credentials in .env produce clean Basic Auth token

- **GIVEN** `.env` contains `OPENOBSERVE_ROOT_USER="admin@iqoqo.local"` or `OPENOBSERVE_ROOT_PASSWORD="secret"` with surrounding quotes
- **WHEN** `ensure_env_secrets()` computes `OPENOBSERVE_BASIC_AUTH`
- **THEN** the quotes are stripped before Base64 encoding and before writing `OPENOBSERVE_BASIC_AUTH`

#### Scenario: Running OpenObserve with drifted volume credentials emits actionable warning

- **GIVEN** OpenObserve is reachable on `OPENOBSERVE_HOST_PORT` (`5080`) and rejects `OPENOBSERVE_BASIC_AUTH` with HTTP `401` or `403`
- **WHEN** `probe_openobserve_auth()` runs during secret verification
- **THEN** it logs a warning identifying the credential mismatch between `.env` and the `openobserve_data` volume and points the operator to `make monitoring-reset-auth`

### Requirement: End-to-End Authenticated OpenObserve and OTel Collector Verification in `make status`
`scripts/iqoqo-status.sh` MUST verify OpenObserve authentication using an authenticated API endpoint (`POST /api/default/_search`) in addition to `/healthz`, and MUST inspect `otel-collector` container logs for recent export failures (`Exporting failed` or `401`).

#### Scenario: Invalid OPENOBSERVE_BASIC_AUTH is flagged as FAIL by make status

- **GIVEN** the `openobserve` container is running and `/healthz` returns `200`, but `POST /api/default/_search` with `Authorization: Basic ${oo_auth}` returns HTTP `401` or `403`
- **WHEN** `scripts/iqoqo-status.sh` evaluates the Observability Stack
- **THEN** it records a `fail` check for OpenObserve Authentication rather than passing on unauthenticated `/healthz` alone

#### Scenario: OTel Collector export failures in recent logs are surfaced by make status

- **GIVEN** the `otel-collector` container is running and its recent logs (`--since 5m`) contain `Exporting failed`
- **WHEN** `scripts/iqoqo-status.sh` evaluates the OTel Collector
- **THEN** it reports a `warn` or `fail` check indicating telemetry export errors

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
