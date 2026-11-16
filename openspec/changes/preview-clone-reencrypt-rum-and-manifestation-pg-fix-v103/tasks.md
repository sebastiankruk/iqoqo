# Tasks: Preview Clone Re-encryption, RUM Provisioning, Manifestation PG Fix & Status Hygiene (`C122` — Target: `v1.0.3`)

## 1. Backend Manifestation Dialect Fix

- [x] 1.1 Update `app/api/manifestations.py` (`get_manifestation_detail`) to resolve dialect via `db.session.get_bind()` instead of `db.session.bind`, and add a pytest regression test verifying PostgreSQL dialect routing when `db.session.bind` is `None`.

## 2. Preview Clone Reconciliation & RUM Provisioning

- [x] 2.1 Update `scripts/iqopretest.sh` to pass `DEPLOY_DIR="$DST_LOC"` to `make status preview` and probe `/api/default/_search` consistently for OpenObserve auth mismatch detection; verify `bash -n scripts/iqopretest.sh` passes.
- [x] 2.2 Update `scripts/iqopretest.sh` to keep `$DST_LOC/.env` authoritative (no merge from `.env.preview`), fetch source `SECRET_KEY` in-memory when `SKIP_CLONE != 1` to decrypt and re-encrypt cloned `InstanceSettings` rows into preview `SECRET_KEY`, push `$DST_LOC/.env` `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, `OPENOBSERVE_*`, and any explicitly configured lookup keys to DB, and audit external lookup + Google OAuth credential readiness while keeping AI keys optional.
- [x] 2.3 Update `Makefile` (`preview-up`) to start `docker-compose.monitoring.yml` before `provision_rum_token.py` unless `OTEL_TRACES_EXPORTER=none`, pass `MODE=preview`, and default `OPENOBSERVE_RUM_SITE` from `https://` `NEXT_PUBLIC_FRONTEND_URL` when unset; verify `tests/test_infra_config.py` and `tests/test_rum_token_provisioning.py` pass.

## 3. Status Check Hygiene (`make status`)

- [x] 3.1 Remove unused `IQOQO_SECRET_KEY` from `.env.example` and `.env.status-classes`, and add `internal` class in `.env.status-classes` for dev/test/runtime-injected flags (`IQOQO_AI_MODE`, `TESTING`, `E2E_RESET_SECRET`, `DATABASE_URL_TEST`, `FLASK_DEBUG`, `SQLALCHEMY_ECHO`, `RATELIMIT_ENABLED`, `ALLOW_PROD_*`, `MODE`, `APP_VERSION`, `OPENOBSERVE_RUM_CLIENT_TOKEN`).
- [x] 3.2 Update `scripts/iqoqo-status.sh` to hide `Defaulted`, `Optional`, `Internal`, and `Empty` variable lists by default, reveal them only under `--all-env` / `--verbose` / `IQOQO_STATUS_VERBOSE=1`, and report live `OPENOBSERVE_RUM_CLIENT_TOKEN` status from the running `frontend` container under `Observability Stack`.
- [x] 3.3 Update `tests/test_infra_config.py`, `tests/bash/iqoqo_status.bats`, and `docs/OPERATIONS.md` / `docs/CHANGELOG.md` to cover the new classification and quiet-by-default behavior; verify `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make secret-scan`, and `IQOQO_AI_MODE=1 make test-parallel` pass.

## 4. Canonical Origin (`BASE_URL`), `DATABASE_URL` Derivation & `presync-check` Targeting

- [x] 4.1 Add `app/db/env.py` (`resolve_database_url()`, `ensure_database_url_env()`, `resolve_frontend_url()`, `resolve_public_app_url()`) and wire it into `app/db/__init__.py`, `app/config.py`, `app/core/mail_service.py`, `app/api/auth.py`, `app/api/items.py`, and `deploy/docker-entrypoint.sh`; add unit tests verifying `DATABASE_URL` derivation (including percent-encoding) and `BASE_URL` fallbacks.
- [x] 4.2 Propagate `BASE_URL` fallbacks in `docker-compose.yml`, `docker-compose.monitoring.yml`, `Makefile` (`preview-up`), `scripts/provision_rum_token.py`, `scripts/iqoqo-status.sh`, and `scripts/iqoqo_installer.py`; update `.env.status-classes` (`BASE_URL=required`, `NEXT_PUBLIC_FRONTEND_URL=default`, `PUBLIC_APP_URL=default`, `DATABASE_URL=default`, `NEXTAUTH_URL=internal`) and wire `DIR`/`DEPLOY_DIR`/`ENV_FILE` into `Makefile` `presync-check`.
- [x] 4.3 Add tests covering `BASE_URL` fallbacks, `DATABASE_URL` derivation, `.env.status-classes` updates, and `make presync-check DIR=...`; update `docs/OPERATIONS.md` and `docs/CHANGELOG.md`, verify lint/secret-scan/tests pass, and push to PR #428.
