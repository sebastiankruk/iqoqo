## Why

Running `iqoclone preview` followed by `make start preview prebuilt` leaves the preview stack with an unhealthy observability pipeline, disabled Browser RUM, and undecryptable `InstanceSettings` rows because production-cloned database rows, OpenObserve volume credentials, and prebuilt Compose environments are not reconciled against the local `.env` / `.env.preview` file—unlike the full flow in `scripts/iqopretest.sh`. Aligning all preview clone, prebuilt startup, auth-reset, and status diagnostic paths removes manual key intervention and eliminates partial secret-drift blind spots in `v1.1.1`.

## What Changes

- Factor the preview secret-reconciliation, OpenObserve auth verification/reset, RUM token provisioning, and selective container recreation flow into a shared `make preview-reconcile` entrypoint used across `scripts/iqopretest.sh`, `make preview-up`, and prebuilt/cloned preview operator workflows (`make start preview prebuilt`, `make clone` follow-up).
- Add `--skip-build` to `scripts/iqopretest.sh` so prebuilt/GHCR preview verification runs without triggering local `make docker-build-preview`.
- Protect cloned `InstanceSettings` rows when `SRC_SECRET_KEY` is unavailable (preserving undecryptable rows with an explicit warning unless an explicit purge flag is provided, instead of silently deleting recoverable credentials), while continuing to pass `SRC_SECRET_KEY` exclusively via stdin (`reconcile_preview_settings.py`) and enforcing `CONFIG_KEY_BLOCKLIST` and authoritative `$DST_LOC/.env` overrides.
- Harden env-file handling (`scripts/ensure_env_secrets.py`, `Makefile` prebuilt/reset targets, and `docker-compose.prebuilt.yml`) to enforce `0600` permissions on `.env` files (resolving symlinks) and prevent empty-string `IMAGE_PREFIX=` in `.env.preview` from overriding the default `ghcr.io/sebastiankruk/` registry prefix.
- Bring `monitoring-credential-hygiene` into parity with OpenObserve `v0.91.5`'s four-class root password policy (`is_openobserve_password_strong`, `generate_openobserve_password`, and `--enforce-openobserve-password-policy` strictly on auth reset while preserving working existing passwords on routine startup).
- Fix `Makefile` `monitoring-reset-auth` and post-reconcile container reloads to use `docker compose ... up -d --force-recreate --no-deps` for `openobserve`, `otel-collector`, `web`, `worker`, and `frontend` (replacing stale `docker start` / `docker restart`), capture `provision_rum_token.py` stdout without leaking `RUM_CLIENT_TOKEN` to terminal logs, and pass `--project-directory $(DEPLOY_DIR)`.
- Harden `scripts/iqoqo-status.sh` and `Makefile` `status`: probe all encrypted `InstanceSettings` rows via `check_encrypted_settings_drift()` instead of a single sample row, resolve DB `OPENOBSERVE_BASIC_AUTH` via `docker exec "$web_cname"` (using `/usr/src/app`) rather than host `python3`, preserve `--deploy-dir $(DEPLOY_DIR)` in the `Makefile` fallback `status` branch, and surface `Browser RUM` and `AI / Vision & OCR Providers` accurately.

## Capabilities

### New Capabilities

None — all requirements extend existing capabilities without introducing new domain or infrastructure capability namespaces.

### Modified Capabilities

- `preview-clone-reencrypt-and-status-hygiene`: Generalize preview clone reconciliation (`make preview-reconcile`, `iqopretest.sh --skip-build`, `make preview-up`, and post-clone workflows), preserve undecryptable rows when `SRC_SECRET_KEY` is missing unless purge is explicitly requested, enforce `0600` permissions on env files, and require selective container `--force-recreate --no-deps` after reconciliation or RUM updates.
- `prebuilt-env-propagation-and-secret-decrypt-guard`: Extend `make start preview prebuilt` / `make start prod prebuilt` parity (monitoring pre-start, RUM provisioning, `0600` env permissions, `IMAGE_PREFIX` empty-string guard, and container-based reconciliation preserving the host-Python-free prebuilt contract), and update `Status Detects Secret-Key Mismatch` so `make status` probes all encrypted `InstanceSettings` rows via `check_encrypted_settings_drift()`.
- `monitoring-credential-hygiene`: Update `Auto-provisioned persistent credential lifecycle` from `secrets.token_urlsafe(32)` to OpenObserve `v0.91.5` four-class password generation/validation (`is_openobserve_password_strong`, `generate_openobserve_password`), enforcing rotation only under `--enforce-openobserve-password-policy` while preserving existing working passwords during routine startup and enforcing `0600` permissions on modified env files.
- `openobserve-telemetry-and-rum-resilience`: Update `monitoring-reset-auth` to recreate `openobserve`, `otel-collector`, `web`, `worker`, and `frontend` via `docker compose up -d --force-recreate --no-deps`, capture `provision_rum_token.py` stdout cleanly without leaking `RUM_CLIENT_TOKEN` to terminal output, sync `OPENOBSERVE_BASIC_AUTH` to `InstanceSettings`, and harden `iqoqo-status.sh` DB credential fallback (`docker exec "$web_cname"`), `--deploy-dir` propagation, and `Browser RUM` diagnostics.

## Impact

- **Deployment & Scripts:** `Makefile` (`start` prebuilt branch, `preview-up`, `preview-reconcile`, `monitoring-reset-auth`, `status`, `clone`), `scripts/iqopretest.sh`, `scripts/clone.sh`, `scripts/reconcile_preview_settings.py`, `scripts/ensure_env_secrets.py`, `scripts/iqoqo-status.sh`, `docker-compose.prebuilt.yml`.
- **Backend Settings Inspection:** `app/db/settings.py` (`check_encrypted_settings_drift()` already exists and becomes the canonical multi-row probe target for `iqoqo-status.sh`).
- **Tests:** `tests/test_reconcile_preview_settings.py`, `tests/test_docker_compose_config.py`, `tests/test_settings_decrypt_failure.py`, `tests/test_config_service.py`, `tests/test_scripts.py`, `tests/test_infra_config.py`, `tests/bats/iqoqo_status.bats`, `tests/bats/clone.bats`, `tests/bats/test_makefile_prebuilt.bats`, `tests/bats/makefile_tooling.bats`, `tests/bats/rum_token_provisioning.bats`.
- **Ontological & Domain Boundaries:** Pure infrastructure, secrets lifecycle, and observability parity; zero FRBR schema, API route, or database migration changes.
