## Why

A real preview run (`scripts/iqopretest.sh --dst-loc /opt/preview.iqoqo`) uncovered four coupled defects that broke manifestation detail pages, Google OAuth login, OpenObserve telemetry/RUM provisioning, and `make status` signal-to-noise:

1. **Manifestation 500 ("Edition not found"):** `app/api/manifestations.py` (`get_manifestation_detail`) checks `db.session.bind.dialect.name`, which is `None` in SQLAlchemy 2.0, causing PostgreSQL deployments to emit SQLite's `json_extract()` and fail with HTTP 500 on every manifestation page.
2. **Cloned PROD secrets wiped & local admin/OAuth not pushed:** `scripts/iqopretest.sh` reconciles `InstanceSettings` against container env only; when `$DST_LOC/.env` uses a local `SECRET_KEY` different from PROD, every cloned `InstanceSettings` row raises `InvalidToken` and is deleted—wiping lookup API credentials (`Discogs`, `TMDB`, `BGG`, `Google Books`, `Allegro`, `UPC`, `Rebrickable`). Meanwhile, `$DST_LOC/.env` local overrides (`GOOGLE_CLIENT_ID`/`SECRET`, `ADMIN_EMAIL`/`PASSWORD`) were not reliably reconciled to DB.
3. **Observability & RUM provisioning drift:** `scripts/iqopretest.sh` ran `make status preview` without `DEPLOY_DIR="$DST_LOC"`, checking `/opt/pre.iqoqo/.env` instead of `/opt/preview.iqoqo/.env` (producing HTTP 401 on OpenObserve Auth). In `Makefile` `preview-up`, `docker-compose.monitoring.yml` only pre-started when `OTEL_TRACES_EXPORTER=otlp`, leaving `provision_rum_token.py` without OpenObserve and leaving `OPENOBSERVE_RUM_CLIENT_TOKEN` unset on `frontend`.
4. **`make status` env noise:** `scripts/iqoqo-status.sh` dumps 60+ `Defaulted`, `Optional`, and `Empty` variable names (including dev/test flags like `IQOQO_AI_MODE`/`TESTING`, unused `IQOQO_SECRET_KEY`, optional AI keys, and runtime-injected `OPENOBSERVE_RUM_CLIENT_TOKEN`) on every run instead of only when requested.

## What Changes

- **Manifestation detail PostgreSQL fix:** Use `db.session.get_bind()` in `app/api/manifestations.py` (`get_manifestation_detail`) so PostgreSQL uses `Item.meta["total_reading_minutes"].astext` instead of SQLite `json_extract()`.
- **Preview clone re-encryption & `$DST_LOC/.env` DB sync (`scripts/iqopretest.sh`):**
  - Keep `$DST_LOC/.env` authoritative (never merge repo `.env.preview` over `$DST_LOC/.env`).
  - When cloning from source (`SKIP_CLONE != 1`), read source `SECRET_KEY` in-memory to decrypt cloned PROD `InstanceSettings` rows and re-encrypt them with preview's local `SECRET_KEY` (never logging or persisting source `SECRET_KEY`).
  - Push local `$DST_LOC/.env` overrides into DB: `ADMIN_EMAIL`/`ADMIN_PASSWORD` into `User`, and `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, `OPENOBSERVE_*`, plus any explicitly set lookup keys in `$DST_LOC/.env` into `InstanceSettings`.
  - Verify external lookup API credentials and Google OAuth readiness after reconciliation (reporting missing lookup/Google creds loudly while leaving AI keys like `OPENAI_API_KEY`/`GEMINI_API_KEY` optional and silent).
  - Pass `DEPLOY_DIR="$DST_LOC"` to `make status preview` and probe `/api/default/_search` consistently for OpenObserve auth resets.
- **Preview RUM provisioning (`Makefile`):** Pre-start `docker-compose.monitoring.yml` in `preview-up` whenever `OTEL_TRACES_EXPORTER` is not `none`, pass `MODE=preview`, and default `OPENOBSERVE_RUM_SITE` from `https://` `NEXT_PUBLIC_FRONTEND_URL` when unset so `OPENOBSERVE_RUM_CLIENT_TOKEN` is provisioned into `frontend`.
- **`make status` hygiene (`scripts/iqoqo-status.sh`, `.env.status-classes`, `.env.example`):**
  - Suppress `Defaulted`, `Optional`, `Internal`, and `Empty` variable lists by default; expose them via `--all-env` / `--verbose` (or `IQOQO_STATUS_VERBOSE=1`).
  - Add `internal` classification in `.env.status-classes` for dev/test/runtime-injected flags (`IQOQO_AI_MODE`, `TESTING`, `E2E_RESET_SECRET`, `DATABASE_URL_TEST`, `FLASK_DEBUG`, `SQLALCHEMY_ECHO`, `RATELIMIT_ENABLED`, `ALLOW_PROD_*`, `MODE`, `APP_VERSION`, `OPENOBSERVE_RUM_CLIENT_TOKEN`, `NEXTAUTH_URL`) and remove unused `IQOQO_SECRET_KEY` from `.env.example` and `.env.status-classes`.
  - Probe live `frontend` container for `OPENOBSERVE_RUM_CLIENT_TOKEN` in the Observability Stack section instead of reporting an empty `.env` placeholder.
- **Canonical `BASE_URL` & `DATABASE_URL` derivation + `presync-check` `DIR` support:**
  - Treat `BASE_URL` as the single canonical public origin default across backend (`PUBLIC_APP_URL`, `NEXT_PUBLIC_FRONTEND_URL` fallbacks), Docker Compose (`NEXT_PUBLIC_FRONTEND_URL`, `NEXT_PUBLIC_APP_URL`, `APP_URL`, OpenObserve CORS), `Makefile` (`preview-up` RUM site), `scripts/provision_rum_token.py`, `scripts/iqoqo-status.sh`, and `scripts/iqoqo_installer.py`.
  - Derive `DATABASE_URL` from `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` (percent-encoded) when `DATABASE_URL` is unset, in `app/db/env.py`, `app/config.py`, and `deploy/docker-entrypoint.sh`.
  - Wire `DIR=` / `DEPLOY_DIR=` / `ENV_FILE=` into `make presync-check` so operators can verify isolated deploy directories cleanly.

## Capabilities

### New Capabilities

- `preview-clone-reencrypt-and-status-hygiene`: In-memory re-encryption of cloned `InstanceSettings`, authoritative `$DST_LOC/.env` admin/OAuth DB sync, preview RUM provisioning, PostgreSQL manifestation detail fix, and quiet-by-default `make status` environment reporting.

### Modified Capabilities

<!-- Tracked under the new capability for v1.0.3 -->

## Impact

- **Backend:** `app/api/manifestations.py`, `tests/`
- **Tooling / Deploy:** `scripts/iqopretest.sh`, `scripts/iqoqo-status.sh`, `Makefile`, `.env.status-classes`, `.env.example`
- **Tests / Docs:** `tests/test_infra_config.py`, `tests/bash/iqoqo_status.bats`, `tests/bash/scripts_syntax.bats`, `docs/OPERATIONS.md`, `docs/CHANGELOG.md`
