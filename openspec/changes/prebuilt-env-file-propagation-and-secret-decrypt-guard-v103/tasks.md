# Tasks: Prebuilt ENV_FILE Propagation & Secret Decrypt Guard (`C119` — P0, Target: `v1.0.3`)

## 1. Phase 1 — Operator Recovery (docs)

- [ ] 1.1 Document the recreate command (`APP_VERSION=1.0.2 ENV_FILE=.env.prod docker compose -p iqoqo -f docker-compose.prebuilt.yml --env-file .env.prod up -d --force-recreate web worker frontend`), verification steps, and rollback in `docs/INSTALL.md`.

## 2. Phase 2 — Durable Fix

- [ ] 2.1 Makefile prebuilt `start`: pass `ENV_FILE=$(COMPOSE_ENV_FILE)` to `docker compose pull` and `up -d`.
- [ ] 2.2 `docs/INSTALL.md`: replace raw `docker compose -f docker-compose.prebuilt.yml up -d` one-liners with `make prebuilt prod start` (or show `ENV_FILE`/`--env-file`).
- [ ] 2.3 `docker-compose.yml`: add `APP_VERSION: ${APP_VERSION:-prod}` to `web` and `worker`.
- [ ] 2.4 `scripts/iqoqo-status.sh`: probe one encrypted `InstanceSettings` row and fail with the `ENV_FILE` vs `make migrate-secrets` hint.
- [ ] 2.5 Tests: extend `tests/test_infra_config.py` for `ENV_FILE` propagation and default; unit test that an `InvalidToken` row surfaces as unset plus warning with no secret logged.

## 3. Phase 3 — Hardening (confirm scope with user first)

- [ ] 3.1 Startup env-drift detection with one aggregated `ERROR` containing the remediation command.
- [ ] 3.2 `1.0.3` upgrade note in `docs/CHANGELOG.md`.

## 4. Verification

- [ ] 4.1 `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel` pass.
