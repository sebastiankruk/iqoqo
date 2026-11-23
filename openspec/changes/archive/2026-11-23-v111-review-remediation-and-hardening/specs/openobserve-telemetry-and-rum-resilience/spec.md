## MODIFIED Requirements

### Requirement: OpenObserve Credential Quote Sanitization, Drift Detection, and Non-Destructive Auth Reset

`scripts/ensure_env_secrets.py` MUST strip surrounding quotes when parsing `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, and `OPENOBSERVE_BASIC_AUTH` from `.env`, and MUST probe a running local OpenObserve instance using `OPENOBSERVE_BASIC_AUTH` to detect credential drift against the persistent `openobserve_data` volume. Additionally, `Makefile` SHALL provide a `monitoring-reset-auth` target that enforces `--enforce-openobserve-password-policy` and `0600` permissions on the active env file (`--project-directory $(DEPLOY_DIR)` for `preview`), resets OpenObserve's `/data/db` metadata store while preserving `/data/stream` parquet telemetry files, recreates `openobserve`, `otel-collector`, `web`, `worker`, and `frontend` via `docker compose ... up -d --force-recreate --no-deps` so updated environment variables take effect, syncs rotated `OPENOBSERVE_BASIC_AUTH` into `InstanceSettings` by piping the secret via `stdin` (never via `-e OO_BASIC_AUTH` CLI arguments visible in `ps aux`), and re-provisions the RUM token by capturing `provision_rum_token.py` stdout cleanly without leaking `RUM_CLIENT_TOKEN` to terminal output.

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
- **THEN** the token MUST be delivered via `stdin` to `docker compose ... exec -T web python3` (never passed as `-e OO_BASIC_AUTH=...` on the command line), `OPENOBSERVE_BASIC_AUTH` MUST be synced into encrypted `InstanceSettings`, and `web` / `worker` MUST be force-recreated so their process environments reflect the updated credentials.
