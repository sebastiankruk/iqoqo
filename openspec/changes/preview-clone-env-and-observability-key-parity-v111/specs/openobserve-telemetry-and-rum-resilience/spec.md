## MODIFIED Requirements

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
