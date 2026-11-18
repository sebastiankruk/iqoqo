## Why

After upgrading to `v1.0.2`, all API keys appeared unset and Google login was disabled (`GET /api/auth/providers` -> `{"apple":false,"google":false}`). Root cause (source: `.context/notes/plan/Restore API keys - Google login after 1.0.2 upgrade.md`): `docker-compose.yml` declares `env_file: - ${ENV_FILE:-.env}`. `run.sh prod` exports `ENV_FILE=.env.prod`, but the Makefile **prebuilt** path (`make prebuilt prod start`) passes `--env-file .env.prod` for interpolation only and never exports `ENV_FILE`, so services fell back to `.env` with a different `SECRET_KEY`. Encrypted `InstanceSettings` rows then failed with `InvalidToken`; `ConfigService.get()` correctly fails closed, so every credential resolved to `None`. No data was lost. The `v1.0.2` `docs/INSTALL.md` one-liner (`docker compose -f docker-compose.prebuilt.yml up -d`) has the same defect. P0.

## What Changes

- **Phase 1 — Operator recovery (documentation):** Document recreating `web worker frontend` with `APP_VERSION=1.0.2 ENV_FILE=.env.prod docker compose -p iqoqo -f docker-compose.prebuilt.yml --env-file .env.prod up -d --force-recreate web worker frontend`, with verification steps and rollback.
- **Phase 2 — Durable fix:**
  - Makefile prebuilt `start`: pass `ENV_FILE=$(COMPOSE_ENV_FILE)` to both `docker compose pull` and `up -d`.
  - `docs/INSTALL.md`: replace raw compose one-liners with `make prebuilt prod start` (or show required `ENV_FILE`/`--env-file`).
  - `docker-compose.yml`: add `APP_VERSION: ${APP_VERSION:-prod}` to `web`/`worker` (API reported `0.8.4` while running `1.0.2`).
  - `scripts/iqoqo-status.sh` (`make status`): probe one encrypted `InstanceSettings` row and fail loudly with a remediation hint (`ENV_FILE` mismatch vs `make migrate-secrets`).
  - Tests: extend `tests/test_infra_config.py` for `ENV_FILE` propagation; add a unit test that an `InvalidToken` row surfaces as "unset" plus a warning.
- **Phase 3 — Hardening (confirm scope before implementing):** startup env-drift detection logging `ERROR` with the exact remediation command; `1.0.3` upgrade note warning operators not to re-run the raw compose one-liner on an existing deployment and never to rotate `SECRET_KEY` without `make migrate-secrets`.
- **Non-goals:** no rotation of `SECRET_KEY`/`JWT_SECRET_KEY`/`AUTH_SECRET`, no DB edits, no image changes, no schema migrations.

## Capabilities

### New Capabilities

- `prebuilt-env-propagation-and-secret-decrypt-guard`: `ENV_FILE` propagation in prebuilt deployments, `APP_VERSION` wiring, encrypted-row status probe, and verified fail-closed handling of undecryptable secrets.

### Modified Capabilities

<!-- Tracked under the new capability for v1.0.3 -->

## Impact

- **Build and deploy:** `Makefile`, `docker-compose.yml`, `docker-compose.prebuilt.yml`, `docs/INSTALL.md`
- **Tooling:** `scripts/iqoqo-status.sh`
- **Backend:** `ConfigService.get()` behavior is verified, not changed
- **Tests:** `tests/test_infra_config.py`, new `InvalidToken` unit test
- **Security:** secret values are never logged; encryption at rest unchanged
