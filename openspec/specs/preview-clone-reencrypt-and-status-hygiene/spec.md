# preview-clone-reencrypt-and-status-hygiene Specification

## Purpose
Defines reliable preview database clone re-encryption, authoritative destination `.env` admin and Google OAuth synchronization, OpenObserve RUM token provisioning, PostgreSQL manifestation detail querying, and concise default `make status` reporting.

## Requirements

### Requirement: Manifestation Detail Resolves Active Database Dialect

`GET /api/manifestations/<manifestation_id>` SHALL resolve the active SQLAlchemy engine dialect via session bind resolution (`get_bind()`) rather than `session.bind`, so PostgreSQL deployments query JSON metadata using PostgreSQL operators rather than SQLite `json_extract()`.

#### Scenario: Manifestation detail succeeds on PostgreSQL

- **WHEN** `GET /api/manifestations/<id>` executes against a PostgreSQL session where `session.bind` is `None`
- **THEN** the endpoint MUST resolve the PostgreSQL dialect via `get_bind()` and return HTTP 200 with the manifestation payload rather than failing with `UndefinedFunction`.

### Requirement: Preview Clone Preserves Lookup Secrets and Applies Authoritative Destination Overrides

`scripts/iqopretest.sh` SHALL treat `$DST_LOC/.env` as authoritative without merging local `.env.preview` into it, SHALL re-encrypt cloned `InstanceSettings` rows from source `SECRET_KEY` to destination `SECRET_KEY` in-memory when cloning, and SHALL push destination `ADMIN_EMAIL`/`ADMIN_PASSWORD` and `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (plus any explicitly configured lookup/observability overrides in `$DST_LOC/.env`) into the preview database.

#### Scenario: Cloned lookup API keys survive preview SECRET_KEY rotation

- **GIVEN** a production database cloned from source into preview with `InstanceSettings` encrypted under source `SECRET_KEY`
- **WHEN** `scripts/iqopretest.sh` reconciles encrypted settings
- **THEN** cloned lookup credentials MUST be decrypted in-memory using source `SECRET_KEY`, re-encrypted under preview `SECRET_KEY`, and retained in `InstanceSettings` without writing source `SECRET_KEY` to disk or logs.

#### Scenario: Destination OAuth and Admin credentials override cloned production values

- **GIVEN** `$DST_LOC/.env` configures preview `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `GOOGLE_CLIENT_ID`, and `GOOGLE_CLIENT_SECRET`
- **WHEN** `scripts/iqopretest.sh` finishes reconciliation
- **THEN** the preview `User` admin account and `InstanceSettings` OAuth entries MUST reflect `$DST_LOC/.env` rather than production values.

#### Scenario: Status check uses destination deploy directory

- **GIVEN** `scripts/iqopretest.sh --dst-loc /opt/preview.iqoqo`
- **WHEN** `iqopretest.sh` invokes `make status preview`
- **THEN** it MUST pass `DEPLOY_DIR="$DST_LOC"` so OpenObserve auth and environment checks read `/opt/preview.iqoqo/.env`.

### Requirement: Preview Startup Provisions Browser RUM Token

`make preview-up` SHALL ensure the monitoring stack is running before invoking `scripts/provision_rum_token.py` unless `OTEL_TRACES_EXPORTER=none`, and SHALL supply `MODE=preview` and a validated public `https://` `OPENOBSERVE_RUM_SITE` derived from `NEXT_PUBLIC_FRONTEND_URL` when unset so `OPENOBSERVE_RUM_CLIENT_TOKEN` is populated in the `frontend` container.

#### Scenario: Preview frontend receives provisioned RUM token

- **GIVEN** `$DEPLOY_ENV_FILE` configures `NEXT_PUBLIC_FRONTEND_URL=https://preview.iqoqo.cc` without explicit `OPENOBSERVE_RUM_SITE`
- **WHEN** `make preview-up` runs
- **THEN** OpenObserve MUST be started beforehand and `provision_rum_token.py` MUST inject a non-empty `OPENOBSERVE_RUM_CLIENT_TOKEN` into `frontend`.

### Requirement: Status Check Suppresses Non-Actionable Environment Noise by Default

`scripts/iqoqo-status.sh` SHALL print only `Configured` counts and `Missing (required)` warnings by default in the Environment Configuration section, SHALL classify dev/test/internal flags and runtime-injected `OPENOBSERVE_RUM_CLIENT_TOKEN` as `internal`, SHALL report live `OPENOBSERVE_RUM_CLIENT_TOKEN` status from the running `frontend` container, and SHALL reveal `Defaulted`, `Optional`, `Internal`, and `Empty` lists only when `--all-env` or `--verbose` (or `IQOQO_STATUS_VERBOSE=1`) is requested.

#### Scenario: Default status hides defaulted, optional, and AI credential lists

- **WHEN** `make status` runs without `--all-env` or `--verbose`
- **THEN** the output MUST NOT print the `Defaulted`, `Optional`, `Internal`, or `Empty` variable name lists, and MUST NOT flag `OPENAI_API_KEY`, `GEMINI_API_KEY`, `IQOQO_AI_MODE`, `TESTING`, or `OPENOBSERVE_RUM_CLIENT_TOKEN` as missing configuration.

#### Scenario: Verbose status reveals full classification lists

- **WHEN** `scripts/iqoqo-status.sh --all-env` (or `--verbose`) runs
- **THEN** the Environment Configuration section MUST display the `Defaulted`, `Optional`, `Internal`, and `Empty` lists for operator inspection.

### Requirement: BASE_URL Acts as Canonical Origin Default

All instance origin settings (`NEXT_PUBLIC_FRONTEND_URL`, `NEXT_PUBLIC_APP_URL`, `APP_URL`, `PUBLIC_APP_URL`) SHALL fall back to `BASE_URL` when unset across backend services, Docker Compose, RUM provisioning, status checks, and installer probes, while preserving `https://` validation for email links and never trusting request `Host` headers.

#### Scenario: Setting only BASE_URL configures frontend, email links, and RUM site

- **GIVEN** an environment with `BASE_URL=https://preview.iqoqo.cc` and `NEXT_PUBLIC_FRONTEND_URL`, `PUBLIC_APP_URL`, and `NEXTAUTH_URL` unset
- **WHEN** the backend resolves `public_origin()`, OAuth redirect URLs, or `preview-up` RUM site
- **THEN** they MUST resolve to `https://preview.iqoqo.cc` without requiring duplicate URL variables.

### Requirement: DATABASE_URL Derives from POSTGRES_* Variables When Unset

When `DATABASE_URL` is unset and `POSTGRES_PASSWORD` is configured, the backend and container entrypoint SHALL derive `postgresql://<user>:<percent-encoded-password>@<host>:<port>/<db>` from `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` before SQLAlchemy models evaluate schema prefixes.

#### Scenario: Omitting DATABASE_URL works with POSTGRES_* credentials

- **GIVEN** `DATABASE_URL` is unset and `POSTGRES_USER=iqoqo`, `POSTGRES_PASSWORD=p@ss:word`, `POSTGRES_DB=iqoqo` are set
- **WHEN** `resolve_database_url()` runs
- **THEN** it MUST return `postgresql://iqoqo:p%40ss%3Aword@db:5432/iqoqo` and populate `DATABASE_URL` before model schema binding.

### Requirement: Makefile presync-check Respects Target Directory

`make presync-check` SHALL pass `--env-file` pointing to `ENV_FILE`, else `$(DIR)/.env`, else overridden `$(DEPLOY_DIR)/.env`, else `.env`.

#### Scenario: Running make presync-check with DIR targets that directory

- **WHEN** `make presync-check DIR=/opt/preview.iqoqo` is invoked
- **THEN** `scripts/iqoqo_installer.py --presync-check` MUST validate `/opt/preview.iqoqo/.env` rather than repo-root `.env`.
