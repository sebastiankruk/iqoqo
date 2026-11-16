## Context

See `proposal.md`. Live inspection of `iqoqo-preview-web-1`, `iqoqo-preview-frontend-1`, `/opt/preview.iqoqo/.env`, and `scripts/iqopretest.sh` revealed:
- `app/api/manifestations.py:380` relies on `db.session.bind`, which is `None` in SQLAlchemy 2.0, breaking `GET /api/manifestations/<id>` on PostgreSQL.
- `scripts/iqopretest.sh` runs `make status preview` without `DEPLOY_DIR="$DST_LOC"`, causing status checks to read `/opt/pre.iqoqo/.env` instead of `/opt/preview.iqoqo/.env`, and deletes every cloned `InstanceSettings` row that fails decryption under preview's `SECRET_KEY`.
- `Makefile` `preview-up` gates pre-starting `docker-compose.monitoring.yml` on `OTEL_TRACES_EXPORTER=otlp`, so minimal `$DST_LOC/.env` files never start OpenObserve before `provision_rum_token.py` runs.
- `scripts/iqoqo-status.sh` emits full `Defaulted` and `Optional` variable lists unconditionally and includes dev/test/internal flags and dead `IQOQO_SECRET_KEY`.

## Goals / Non-Goals

**Goals:**
- Fix PostgreSQL dialect detection in `get_manifestation_detail`.
- Preserve cloned PROD lookup credentials via in-memory re-encryption while keeping `$DST_LOC/.env` strictly authoritative over repo `.env.preview`.
- Ensure preview `ADMIN_*` and `GOOGLE_CLIENT_*` from `$DST_LOC/.env` are pushed to DB and missing lookup/OAuth credentials are flagged clearly (while AI keys stay optional).
- Provision `OPENOBSERVE_RUM_CLIENT_TOKEN` reliably in `make preview-up` and verify it in `make status`.
- Make `make status` quiet by default for defaulted/optional/internal/AI variables while offering `--all-env` / `--verbose` for full audits.

**Non-Goals:**
- Merging repo `.env.preview` into `$DST_LOC/.env`.
- Relaxing `provision_rum_token.py` security invariants (e.g., loopback targets are still rejected in `preview`/`prod`).
- Persisting `SRC_SECRET_KEY` or `OPENOBSERVE_RUM_CLIENT_TOKEN` to `.env` files on disk.

## Decisions

1. **Dialect resolution (`app/api/manifestations.py`):** Use `db.session.get_bind()`, matching `app/core/data_manager.py:1957` and `app/core/account_tokens.py:344`.
2. **In-memory re-encryption via stdin JSON (`scripts/iqopretest.sh`):** Read `SRC_SECRET_KEY` (when `SKIP_CLONE != 1`) and `$DST_LOC/.env` key-value overrides in shell, pass them to `docker compose ... exec -T web python3 -c ...` over `stdin` JSON so secrets never appear in `argv`, `/proc/<pid>/cmdline`, or disk. Re-encrypt cloned `InstanceSettings` rows that decrypt with `SRC_SECRET_KEY` into preview `SECRET_KEY`; upsert `$DST_LOC/.env` overrides (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OPENOBSERVE_BASIC_AUTH`, `OPENOBSERVE_ROOT_PASSWORD`, and any explicitly set lookup keys); sync `ADMIN_EMAIL`/`ADMIN_PASSWORD` to `User` (via `init_auth` logic); and warn if Google OAuth or core lookup providers remain unconfigured in DB+env.
3. **Preview RUM provisioning (`Makefile`):** In `preview-up`, start `docker-compose.monitoring.yml` before `provision_rum_token.py` whenever `OTEL_TRACES_EXPORTER` is not `"none"`. Export `MODE=preview` and derive `OPENOBSERVE_RUM_SITE` from `NEXT_PUBLIC_FRONTEND_URL` only when unset and `NEXT_PUBLIC_FRONTEND_URL` begins with `https://` (same-origin `/rum/:path*` proxy in `frontend/next.config.ts`).
4. **Status hygiene (`scripts/iqoqo-status.sh`, `.env.status-classes`, `.env.example`):** Add `internal` class to `.env.status-classes` for dev/test/runtime-injected variables (`IQOQO_AI_MODE`, `TESTING`, `E2E_RESET_SECRET`, `DATABASE_URL_TEST`, `FLASK_DEBUG`, `SQLALCHEMY_ECHO`, `RATELIMIT_ENABLED`, `ALLOW_PROD_*`, `MODE`, `APP_VERSION`, `OPENOBSERVE_RUM_CLIENT_TOKEN`, `NEXTAUTH_URL`). Remove unused `IQOQO_SECRET_KEY`. Default `iqoqo-status.sh` to printing `Configured` and `Missing (required)` only; require `--all-env` / `--verbose` / `IQOQO_STATUS_VERBOSE=1` for `Defaulted`, `Optional`, `Internal`, and `Empty` lists. Check live `frontend` container env for `OPENOBSERVE_RUM_CLIENT_TOKEN` under `Observability Stack`.
5. **Decision for future features — `BASE_URL` as single canonical origin default:** Operators SHALL only need to set `BASE_URL` for a single-origin deployment. `NEXT_PUBLIC_FRONTEND_URL`, `NEXT_PUBLIC_APP_URL`, `APP_URL`, and `PUBLIC_APP_URL` all default from `BASE_URL` (with `NEXT_PUBLIC_FRONTEND_URL` taking precedence when explicitly overridden). `mail_service.public_origin()` still enforces `https://` (or `http://localhost`) and rejects request `Host` headers. `NEXTAUTH_URL` is legacy and classified `internal`. Accordingly, `.env.status-classes` marks `BASE_URL=required` and `NEXT_PUBLIC_FRONTEND_URL=default` / `PUBLIC_APP_URL=default`.
6. **Decision for future features — `DATABASE_URL` derived from `POSTGRES_*` when unset:** When `DATABASE_URL` is omitted from `.env` and `POSTGRES_PASSWORD` is configured, `app/db/env.py` (invoked from `app/db/__init__.py` before model `_USE_PG` schema evaluation and from `app/config.py`) and `deploy/docker-entrypoint.sh` automatically synthesize `postgresql://<user>:<quoted_password>@<host>:<port>/<db>` (defaulting host=`db`, port=`5432`, user=`iqoqo`, db=`iqoqo`). `DATABASE_URL` is classified `default` in `.env.status-classes`, while `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` remain `required`.
7. **`make presync-check` directory targeting:** `Makefile` `presync-check` resolves `--env-file` from `ENV_FILE`, else `$(DIR)/.env`, else `$(DEPLOY_DIR)/.env` (when overridden from `/opt/pre.iqoqo`), else `.env`.

## Risks / Trade-offs

- **[Risk] Remote `SRC_HOST` SSH read of `SRC_SECRET_KEY` fails when `SKIP_CLONE=0`** -> Mitigation: fall back gracefully with a warning if `SRC_SECRET_KEY` cannot be read, without deleting rows blindly when `$DST_LOC/.env` doesn't override them unless unrecoverable, and warn clearly about missing lookup credentials.
- **[Risk] Updating `.env.status-classes` to include `internal` breaks existing schema-validation tests** -> Mitigation: update `tests/test_infra_config.py` and `tests/bash/iqoqo_status.bats` in the same change to allow `{"required", "default", "optional", "internal"}` and test `--all-env` vs default output.
