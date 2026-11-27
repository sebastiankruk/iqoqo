## Why

After cloning production into a prebuilt preview host (`/opt/pre.iqoqo`, v1.1.2) and starting with `make start preview prebuilt` or standalone `make preview-reconcile`, `scripts/reconcile_preview_settings.py` prints `✅ Encrypted settings reconciled (re-encrypted: 0, overridden from env: 4, cleared stale: 0)` while leaving 13 cloned production `InstanceSettings` rows undecryptable (`InvalidToken`). Four gaps cause this silent failure:

1. `Makefile` `start` prebuilt preview branch (lines 363–364) pipes `.env.preview` into `reconcile_preview_settings.py --dotenv-stdin 2>/dev/null` without passing `SRC_SECRET_KEY` (and `--dotenv-stdin` reads `os.environ.get("SRC_SECRET_KEY")` inside the `web` container where it is never injected), swallows stderr, and does not force-recreate `web` or `worker` after updating settings.
2. `Makefile` `preview-reconcile` (line 473) defaults `SKIP_CLONE` to `1` (`${SKIP_CLONE:-1}`), so standalone `SRC_LOC=/opt/iqoqo make preview-reconcile` still sends an empty `src_secret_key`; it also invokes host `python3` (lines 490 and 505), breaking on prebuilt hosts without a host Python venv.
3. `Makefile` `preview-reconcile` (lines 491 and 515) hardcodes `APP_VERSION=${APP_VERSION:-preview}` and `monitoring-reset-auth` (line 634) omits `APP_VERSION`, causing prebuilt hosts running tagged GHCR images (e.g., `1.1.2`) with stale `.env.preview` `APP_VERSION` entries to fail pull or downgrade containers during `--force-recreate`.
4. `scripts/reconcile_preview_settings.py` (lines 280–283) prints green `✅ Encrypted settings reconciled` without surfacing `preserved undecryptable: N` in the summary line, and `scripts/clone.sh` (line 296) omits `SRC_LOC`, `SRC_NAME`, and `SRC_HOST` from its printed next-step commands.

## What Changes

- Extend `scripts/reconcile_preview_settings.py --dotenv-stdin` to accept an optional framed first-line stdin header `__IQOQO_SRC_SECRET_KEY__=<value>` (popped before `parse_env_text()`, excluded from `dst_env` and `InstanceSettings`, never written to disk, argv, container environment, or logs) and emit `⚠️ Encrypted settings partially reconciled (re-encrypted: ..., overridden from env: ..., cleared stale: ..., preserved undecryptable: N)` with actionable remediation whenever `preserved_undecryptable` is non-empty.
- Update `Makefile` `start` prebuilt preview branch to resolve `src_secret` via pure shell (`SRC_SECRET_KEY`, else `SRC_LOC` + `SRC_NAME` defaulting to `prod` + optional `SRC_HOST` when `SKIP_CLONE != 1`), stream `{ printf '__IQOQO_SRC_SECRET_KEY__=%s\n' "$$src_secret"; cat "$(ABS_COMPOSE_ENV_FILE)"; }` via bash builtin `printf` (avoiding `/proc/<pid>/cmdline` argv leaks and zero host Python), remove `2>/dev/null` stderr suppression, and force-recreate `web` and `worker` (`--force-recreate --no-deps`) after reconciliation.
- Update `Makefile` `preview-reconcile` to default `SKIP_CLONE` to `0` (`${SKIP_CLONE:-0}`) so explicit `SRC_LOC` works standalone while `scripts/iqopretest.sh --skip-clone` (`SKIP_CLONE=1`) still skips source lookup, switch reconciliation and RUM provisioning (`provision_rum_token.py --mgmt-host openobserve`) to container-executed Python (zero host `python3` dependency), and resolve `APP_VERSION` cleanly in both `preview-reconcile` and `monitoring-reset-auth` (`explicit APP_VERSION` → running `web` container image tag → `$(PREBUILT_TAG)`).
- Update `scripts/clone.sh` preview next-step output to include the exact `SRC_LOC`, `SRC_NAME`, and optional `SRC_HOST` parameters.

## Capabilities

### New Capabilities

None — all changes extend existing preview reconciliation and prebuilt deployment capabilities without introducing new capability namespaces.

### Modified Capabilities

- `preview-clone-reencrypt-and-status-hygiene`: Support stdin-framed `__IQOQO_SRC_SECRET_KEY__=` in `--dotenv-stdin`, default `SKIP_CLONE` to `0` in `make preview-reconcile` (forbidding implicit source-directory discovery when neither `SRC_SECRET_KEY` nor `SRC_LOC` is supplied), emit partial-reconciliation warning summaries with `preserved undecryptable: <N>`, print exact source arguments in `scripts/clone.sh`, execute `preview-reconcile` without host `python3`, and preserve running `APP_VERSION` tags across `preview-reconcile` and `monitoring-reset-auth`.
- `prebuilt-env-propagation-and-secret-decrypt-guard`: Propagate optional `SRC_SECRET_KEY` / `SRC_LOC` via pure-shell stdin framing in `make start preview prebuilt` without host Python/Node or `2>/dev/null` stderr suppression, and force-recreate `web` and `worker` (`--force-recreate --no-deps`) after reconciling `InstanceSettings`.

## Impact

- **Deployment & Scripts:** `scripts/reconcile_preview_settings.py`, `Makefile` (`start` prebuilt `MODE=preview` branch, `preview-reconcile`, `monitoring-reset-auth`), and `scripts/clone.sh`.
- **Tests:** `tests/test_reconcile_preview_settings.py`, `tests/bash/test_makefile_prebuilt.bats`, `tests/bash/makefile_tooling.bats`, `tests/bash/clone.bats`, and `tests/test_infra_config.py`.
- **Ontological & Domain Boundaries:** Infrastructure, secret lifecycle, and Compose tag parity only; zero FRBR schema, API endpoint, or database migration changes.
