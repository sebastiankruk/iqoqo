## Context

See `proposal.md` (`## Why`) for motivation. In the current codebase (`Makefile`, `scripts/clone.sh`, `scripts/iqopretest.sh`, `scripts/reconcile_preview_settings.py`, `scripts/ensure_env_secrets.py`, `scripts/provision_rum_token.py`, `scripts/iqoqo-status.sh`, `docker-compose.prebuilt.yml`, and `app/db/settings.py`), two critical constraints shape the design:

1. **Prebuilt host independence (`tests/bats/test_makefile_prebuilt.bats`):** Existing tests poison host `python`, `python3`, `node`, and `npm` binaries during `make prod start prebuilt` and `make preview start prebuilt` to guarantee standalone prebuilt deployments do not depend on host runtimes.
2. **Container environment immutability:** Docker Compose resolves `env_file` and interpolated `${VAR}` values (including `OPENOBSERVE_ROOT_PASSWORD`, `OPENOBSERVE_BASIC_AUTH`, `SECRET_KEY`, and `OPENOBSERVE_RUM_CLIENT_TOKEN`) only at container creation time. `docker start` and `docker restart` reuse frozen `Config.Env` snapshots.

This design aligns `iqoclone preview` + `make start preview prebuilt`, `make preview-up`, `make monitoring-reset-auth`, `scripts/iqopretest.sh`, and `make status` without breaking standalone prebuilt hosts or violating `iqoqo-devops-sre-expert` zero-trust secret boundaries.

## Goals / Non-Goals

**Goals:**
- Provide a single canonical preview reconciliation workflow (`make preview-reconcile`) shared across `scripts/iqopretest.sh`, `make preview-up`, and post-clone operator flows (`make clone` / `iqoclone preview`).
- Achieve parity in `make start preview prebuilt` (monitoring pre-start, `0600` env permissions, `IMAGE_PREFIX` fallback resilience, OpenObserve auth probe/reset, `InstanceSettings` `.env` sync, and Browser RUM injection) while keeping host `python`/`node` unrequired.
- Enforce stdin-only `SRC_SECRET_KEY` handling, non-destructive preservation of undecryptable cloned rows when `SRC_SECRET_KEY` is absent, and `CONFIG_KEY_BLOCKLIST` isolation.
- Eliminate stale container environments and terminal `RUM_CLIENT_TOKEN` leakage in `monitoring-reset-auth` and `preview-reconcile`.
- Eliminate partial-drift blind spots and host-Python assumptions in `scripts/iqoqo-status.sh` and `Makefile` `status`.

**Non-Goals:**
- Changing FRBR domain models, API endpoints, database schemas, or Alembic migrations.
- Modifying external user-home scripts outside the repository (`/home/sebastiankruk/.local/bin/iqoclone`), except documenting optional wrapper alignment or adding an in-repo entrypoint.
- Automatically migrating `openobserve_data` credentials without explicit reset when an existing volume is already functioning with a legacy password.

## Decisions

### Decision 1: Preview Reconciliation Architecture & Prebuilt Host-Python-Free Parity

- **Options Considered:**
  - **Option A — Shared `make preview-reconcile` target + container-executed reconciliation in `make start preview prebuilt` (Selected):**
    - Factor OpenObserve auth verification/reset, `reconcile_preview_settings.py`, RUM token provisioning, and selective `--force-recreate --no-deps` into `make preview-reconcile` (invoked by `scripts/iqopretest.sh` and post-clone workflows, and optionally triggered via `RECONCILE=1` or automatically on `preview` starts).
    - Keep `make start preview prebuilt` compliant with `tests/bats/test_makefile_prebuilt.bats` by executing Python helpers (`ensure_env_secrets.py`, `reconcile_preview_settings.py`, `provision_rum_token.py`) **inside** the pulled `iqoqo-backend` image (`docker compose ... run --rm --no-deps -T web python3 ...` / `exec -T web python3 ...`), using `openobserve:5080` or host loopback networking for RUM provisioning, and running `chmod 0600` directly in POSIX shell on the resolved env file.
    - Add `--skip-build` to `scripts/iqopretest.sh` so prebuilt GHCR images can be verified end-to-end without `make docker-build-preview`.
  - **Option B — Route `make start preview prebuilt` directly through host-Python `make preview-up` + `scripts/iqopretest.sh`:**
    - Rejected because `make preview-up` invokes host `python3` (`sync_deploy_dir.py`, `pre_deploy_mounts.py`, `ensure_env_secrets.py`, `provision_rum_token.py`), directly breaking `tests/bats/test_makefile_prebuilt.bats` on source-free/Python-less hosts, and `iqopretest.sh` historically requires a local build context.
  - **Option C — Self-reconciliation inside `deploy/docker-entrypoint.sh` of `web`:**
    - Rejected because `web` runs as unprivileged `appuser` without access to the Docker socket: it cannot clear `/data/db` inside `openobserve_data`, cannot recreate sibling containers (`otel-collector`, `openobserve`, `frontend`), cannot inject `OPENOBSERVE_RUM_CLIENT_TOKEN` into `frontend`'s environment, and would require mounting or passing `SRC_SECRET_KEY` via disk/container env (violating non-persistence).

### Decision 2: Missing `SRC_SECRET_KEY` Handling (`preserve` vs. `purge`)

- **Options Considered:**
  - **Option A — Preserve undecryptable rows by default and warn; delete only with `--purge-undecryptable` (Selected):**
    - Currently `scripts/reconcile_preview_settings.py` deletes every non-overridden encrypted row (`db.session.delete(row)`) whenever `src_secret_key` is empty (`SKIP_CLONE=1` or SSH-less `iqoclone preview`). Preserving those rows by default protects cloned lookup API keys if an operator forgets to pass `SRC_SECRET_KEY` on the first run and later re-runs `make preview-reconcile` with `SRC_SECRET_KEY` on stdin. Explicit `.env` overrides (`clean_env`) still overwrite matching keys immediately, and `--purge-undecryptable` remains available for intentional cleanup.
  - **Option B — Keep unconditional deletion when `src_secret_key` is empty:**
    - Rejected because a single `SKIP_CLONE=1` or SSH-less `make start preview prebuilt` permanently destroys cloned provider keys in the preview DB.

### Decision 3: Fernet / Stdin Security Boundaries, `.env` Authority, and `0600` Permissions

- **Stdin-only `SRC_SECRET_KEY`:** `scripts/iqopretest.sh` and `make preview-reconcile` MUST pass `{"src_secret_key": ..., "dst_env": ...}` solely over stdin to `docker compose ... exec -T web env PYTHONPATH=/usr/src/app python3 /usr/src/app/scripts/reconcile_preview_settings.py` and immediately `unset SRC_SECRET_KEY` in the calling shell. `SRC_SECRET_KEY` MUST NEVER be written to `.env`, `/tmp`, CLI `argv`, container `Config.Env`, or logs.
- **Authoritative `$DST_LOC/.env` & `CONFIG_KEY_BLOCKLIST`:** Repo `.env.preview` is never merged into `$DST_LOC/.env`. `reconcile_preview_settings.py` keeps `CONFIG_KEY_BLOCKLIST` (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`) excluded from `ELIGIBLE_SETTING_KEYS`, while overriding `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OPENOBSERVE_ROOT_PASSWORD`, `OPENOBSERVE_BASIC_AUTH`, and any non-empty lookup keys defined in `$DST_LOC/.env`. `OPENOBSERVE_RUM_CLIENT_TOKEN` (`BROWSER_BOUND_TOKEN_KEYS`) is never written to `.env`.
- **`chmod 0600` enforcement:** `scripts/ensure_env_secrets.py` MUST call `os.chmod(file_path.resolve(), 0o600)` whenever writing secrets (resolving `.env -> .env.preview` symlinks), and `Makefile` (`preview-up`, `preview-reconcile`, `monitoring-reset-auth`, `start ... prebuilt`) MUST enforce `0600` on the target env file.
- **`IMAGE_PREFIX` empty-string trap:** `docker-compose.prebuilt.yml` MUST use `${IMAGE_PREFIX:-ghcr.io/sebastiankruk/}` (colon-dash, or Makefile guards empty `IMAGE_PREFIX`) so an empty `IMAGE_PREFIX=` line in `.env.preview` cannot strip the `ghcr.io/sebastiankruk/` prefix during `pull` or `up -d`.

### Decision 4: OpenObserve Password Policy, `monitoring-reset-auth`, RUM Capture, and Selective Force-Recreate

- **Four-class password policy vs. routine start preservation:** `ensure_env_secrets.py` already distinguishes routine starts (`enforce_openobserve_password_policy=False`, preserving existing >=16-char passwords so live `openobserve_data` volumes are never broken) from `monitoring-reset-auth` (`--enforce-openobserve-password-policy`, regenerating weak passwords via `generate_openobserve_password()` before `/data/db` is cleared). Both `monitoring-credential-hygiene` and `openobserve-telemetry-and-rum-resilience` specs are aligned to this exact boundary.
- **Selective `--force-recreate --no-deps`:** Replacing `docker start "${cproject}-openobserve"` and `docker restart "${cproject}-otel-collector"` in `Makefile` `monitoring-reset-auth` with `docker compose --project-directory $(DEPLOY_DIR) ... up -d --force-recreate --no-deps openobserve otel-collector` (and similarly recreating `web`, `worker`, and `frontend` when `.env` secrets or `OPENOBSERVE_RUM_*` change) ensures updated `OPENOBSERVE_ROOT_PASSWORD`, `OPENOBSERVE_BASIC_AUTH`, and `OPENOBSERVE_RUM_CLIENT_TOKEN` take effect immediately without recreating healthy unrelated services like `db` or `redis`.
- **No RUM token stdout leakage:** Both `preview-up` and `monitoring-reset-auth` MUST capture `provision_rum_token.py` stdout via command substitution (`rum_out="$(...)"`), parse `RUM_CLIENT_TOKEN=` / `RUM_SITE=` / `RUM_INSECURE_HTTP=`, export `OPENOBSERVE_RUM_*` to the environment, and recreate `frontend` without ever printing `RUM_CLIENT_TOKEN` to terminal stdout/stderr.

### Decision 5: Multi-Row `InstanceSettings` & Container-Exec Status Diagnostics

- **Replace single-row `next(...)` probe with `check_encrypted_settings_drift()`:** `scripts/iqoqo-status.sh` currently checks only the first encrypted row, masking mixed-key drift (e.g., 2 preview-encrypted rows + 15 prod-encrypted rows). Invoking `app.db.settings.check_encrypted_settings_drift()` inside `docker exec "$web_cname"` checks every encrypted row in one pass and reports all failing key names without exposing values.
- **Container-exec `OPENOBSERVE_BASIC_AUTH` DB fallback:** When `OPENOBSERVE_BASIC_AUTH` is absent from `.env` on non-dev stacks (`preview`, `prod`), `scripts/iqoqo-status.sh` MUST query `InstanceSettings.get_value('OPENOBSERVE_BASIC_AUTH')` via `docker exec "$web_cname"` (using `/usr/src/app` `sys.path`) rather than host `python3`.
- **`Makefile` fallback `--deploy-dir` & raw exit awareness:** The fallback container-extraction branch in `Makefile` `status` MUST pass `$$deploy_arg` (`--deploy-dir $(DEPLOY_DIR)` for `preview`) to the extracted `iqoqo-status.sh`. Status verification steps distinguish raw `iqoqo-status.sh` exit codes (`0` healthy, `1` warnings, `2` errors) from `make status` (which masks exit `1` to `0`).

## Risks / Trade-offs

- **[Risk] Container-side `ensure_env_secrets.py` or `provision_rum_token.py` inside `make start preview prebuilt` needs write access to host `.env.preview` and loopback/Docker-network access to OpenObserve (`:5080`)** → **Mitigation:** Mount/target the resolved env file explicitly during `docker compose run --rm --no-deps --entrypoint python3` (or run `docker exec` on running `web` for DB-only steps) while preserving POSIX `0600` on the host file, and support `OPENOBSERVE_INTERNAL_URL` (`http://openobserve:5080`) when running inside the Compose network vs `127.0.0.1:${OPENOBSERVE_HOST_PORT:-5080}` on host.
- **[Risk] Preserving undecryptable cloned rows when `SRC_SECRET_KEY` is omitted leaves stale keys until a full `preview-reconcile` with `SRC_SECRET_KEY` runs** → **Mitigation:** `ConfigService.get()` already fails closed (`None`) on `InvalidToken` without crashing, `check_encrypted_settings_drift()` flags the exact undecryptable keys in `make status` (`Encrypted settings` fail), and `--purge-undecryptable` allows explicit cleanup when source keys are intentionally abandoned.
- **[Risk] Recreating `web`, `worker`, and `frontend` during `preview-reconcile` / `monitoring-reset-auth` causes brief (<5s) request interruption** → **Mitigation:** Use `--force-recreate --no-deps` scoped strictly to containers whose env/RUM state actually changed, leaving `db`, `redis`, and `nginx` untouched.

## Open Questions

- **External `iqoclone` wrapper (`/home/sebastiankruk/.local/bin/iqoclone`):** Lives outside the git repository (`make clone ...`). Should an in-repo `scripts/iqoclone.sh` (or `make clone-preview` / post-clone prompt in `scripts/clone.sh`) also be added alongside documentation so operators do not rely solely on out-of-repo dotfiles? Deferrable to implementation (`tasks.md` includes updating repo docs/Makefile hook while noting external wrapper alignment).
- **`make migrate-secrets` target name:** Referenced in `app/db/settings.py` and `scripts/iqoqo-status.sh` remediation messages, though no `migrate-secrets` target currently exists in `Makefile`. Implementation can either add `migrate-secrets` as an alias/wrapper around `preview-reconcile` or update the remediation hint if a separate rotation target is out of scope.
