## MODIFIED Requirements

### Requirement: Preview Clone Preserves Lookup Secrets and Applies Authoritative Destination Overrides

`scripts/iqopretest.sh`, `make preview-reconcile`, and preview post-clone reconciliation flows SHALL treat `$DST_LOC/.env` as authoritative without merging local `.env.preview` into it, SHALL re-encrypt cloned `InstanceSettings` rows from source `SECRET_KEY` to destination `SECRET_KEY` in-memory via stdin JSON when `SRC_SECRET_KEY` is supplied, SHALL exclude `CONFIG_KEY_BLOCKLIST` keys (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`) from `InstanceSettings` writes, and SHALL push destination `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, and explicitly configured lookup or observability overrides (`OPENOBSERVE_ROOT_PASSWORD`, `OPENOBSERVE_BASIC_AUTH`) from `$DST_LOC/.env` into the preview database. When `SRC_SECRET_KEY` is missing or empty, undecryptable cloned `InstanceSettings` rows MUST be preserved with a warning rather than silently deleted unless an explicit `--purge-undecryptable` opt-in flag is provided.

#### Scenario: Cloned lookup API keys survive preview SECRET_KEY rotation

- **GIVEN** a production database cloned from source into preview with `InstanceSettings` encrypted under source `SECRET_KEY`
- **WHEN** `scripts/iqopretest.sh` or `make preview-reconcile` reconciles encrypted settings with `SRC_SECRET_KEY` passed on stdin
- **THEN** cloned lookup credentials MUST be decrypted in-memory using source `SECRET_KEY`, re-encrypted under preview `SECRET_KEY`, and retained in `InstanceSettings` without writing source `SECRET_KEY` to disk, argv, container environment variables, or logs.

#### Scenario: Destination OAuth and Admin credentials override cloned production values

- **GIVEN** `$DST_LOC/.env` configures preview `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `OPENOBSERVE_BASIC_AUTH`
- **WHEN** preview reconciliation finishes
- **THEN** the preview `User` admin account and `InstanceSettings` OAuth and OpenObserve entries MUST reflect `$DST_LOC/.env` rather than cloned production values.

#### Scenario: Status check uses destination deploy directory

- **GIVEN** `scripts/iqopretest.sh --dst-loc /opt/preview.iqoqo`
- **WHEN** `iqopretest.sh` invokes `make status preview`
- **THEN** it MUST pass `DEPLOY_DIR="$DST_LOC"` so OpenObserve auth and environment checks read `/opt/preview.iqoqo/.env`.

#### Scenario: Missing SRC_SECRET_KEY preserves undecryptable cloned settings by default

- **GIVEN** a preview database containing cloned `InstanceSettings` rows encrypted under an unavailable source `SECRET_KEY` and reconciliation runs without `SRC_SECRET_KEY` (such as `SKIP_CLONE=1` or an SSH-less `preview-reconcile` invocation without `--purge-undecryptable`)
- **WHEN** `scripts/reconcile_preview_settings.py` executes
- **THEN** it MUST apply authoritative `$DST_LOC/.env` overrides and admin sync, emit a warning listing the count of undecryptable rows left untouched, and MUST NOT delete those rows from `InstanceSettings`.

#### Scenario: Infrastructure blocklist keys in destination env never enter InstanceSettings

- **GIVEN** `$DST_LOC/.env` defines `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, and `JWT_SECRET_KEY`
- **WHEN** `scripts/reconcile_preview_settings.py` processes `dst_env`
- **THEN** those four `CONFIG_KEY_BLOCKLIST` keys MUST NOT be inserted or updated in `InstanceSettings`.

### Requirement: Preview Startup Provisions Browser RUM Token

`make preview-up` and `make preview-reconcile` SHALL ensure the monitoring stack is running before invoking `scripts/provision_rum_token.py` unless `OTEL_TRACES_EXPORTER=none`, SHALL supply `MODE=preview` and a validated public `https://` `OPENOBSERVE_RUM_SITE` derived from `NEXT_PUBLIC_FRONTEND_URL` (or `BASE_URL`) when unset, SHALL capture `provision_rum_token.py` stdout cleanly without leaking `RUM_CLIENT_TOKEN` to terminal logs, and SHALL ensure the `frontend` container is recreated (`--force-recreate --no-deps`) whenever `OPENOBSERVE_RUM_CLIENT_TOKEN` is newly provisioned or changed.

#### Scenario: Preview frontend receives provisioned RUM token

- **GIVEN** `$DEPLOY_ENV_FILE` configures `NEXT_PUBLIC_FRONTEND_URL=https://preview.iqoqo.cc` without explicit `OPENOBSERVE_RUM_SITE`
- **WHEN** `make preview-up` or `make preview-reconcile` runs
- **THEN** OpenObserve MUST be started beforehand, `provision_rum_token.py` stdout MUST be parsed without printing the token to stdout/stderr, and `OPENOBSERVE_RUM_CLIENT_TOKEN` MUST be injected into `frontend`.

#### Scenario: Preview startup recreates frontend cleanly when RUM token changes

- **GIVEN** a running `frontend` container started before OpenObserve was ready or with an empty `OPENOBSERVE_RUM_CLIENT_TOKEN`
- **WHEN** `make preview-reconcile` provisions a valid `RUM_CLIENT_TOKEN`
- **THEN** `frontend` MUST be recreated via `docker compose ... up -d --force-recreate --no-deps frontend` with the exported `OPENOBSERVE_RUM_*` variables so the live container environment carries the token.

## ADDED Requirements

### Requirement: Shared Preview Reconciliation Target and Skip-Build Pretest Parity

`Makefile` SHALL provide a `preview-reconcile` target shared by `scripts/iqopretest.sh`, `make preview-up`, and post-`make clone` / `iqoclone preview` operator workflows to reconcile secrets, verify OpenObserve auth (triggering `monitoring-reset-auth` on HTTP `401` or `403`), sync `InstanceSettings` and admin credentials, provision Browser RUM, and selectively recreate affected containers (`openobserve`, `otel-collector`, `web`, `worker`, `frontend`) via `docker compose ... up -d --force-recreate --no-deps`. Additionally, `scripts/iqopretest.sh` SHALL support a `--skip-build` option to execute the full preview clone/reconcile/status workflow against prebuilt or existing images without invoking `make docker-build-preview`.

#### Scenario: iqopretest --skip-build verifies prebuilt preview stack without rebuilding images

- **GIVEN** prebuilt preview images are already present or pulled in `$DST_LOC`
- **WHEN** an operator invokes `scripts/iqopretest.sh --skip-build --dst-loc /opt/pre.iqoqo`
- **THEN** `iqopretest.sh` MUST skip `make docker-build-preview`, execute clone/startup/reconciliation/status parity checks, and exit `0` when the preview stack is healthy.

#### Scenario: Reconciled containers reload updated env and RUM tokens via force-recreate

- **GIVEN** preview reconciliation updates `.env` credentials or provisions a new `OPENOBSERVE_RUM_CLIENT_TOKEN` while preview containers are already running
- **WHEN** `make preview-reconcile` completes credential and database updates
- **THEN** affected services (`openobserve`, `otel-collector`, `web`, `worker`, `frontend`) MUST be reloaded with `docker compose ... up -d --force-recreate --no-deps` rather than `docker start` or `docker restart`.

### Requirement: Env Files Enforce 0600 Permissions After Secret Reconciliation

`scripts/ensure_env_secrets.py`, `make preview-up`, `make preview-reconcile`, `make monitoring-reset-auth`, and `make start ... prebuilt` SHALL ensure that the target environment file (resolving symlinks such as `.env -> .env.preview`) has `0600` permissions whenever created or updated.

#### Scenario: Secret provisioning tightens target env file permissions to 0600

- **GIVEN** a deployment directory containing `.env.preview` (or `.env` symlinked to `.env.preview`) with permissive mode `0644`
- **WHEN** `ensure_env_secrets.py` modifies the file or `make preview-reconcile` completes
- **THEN** the resolved target env file MUST have POSIX mode `0600`.
