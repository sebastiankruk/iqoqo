## Context

Live inspection of `/opt/pre.iqoqo` (`v1.1.2`, prebuilt preview) after a production clone revealed that `scripts/reconcile_preview_settings.py` logged `✅ Encrypted settings reconciled (re-encrypted: 0, overridden from env: 4, cleared stale: 0)` while leaving 13 cloned `InstanceSettings` rows encrypted under production's `SECRET_KEY` (`InvalidToken` on startup and `None` on runtime lookup). Only the 4 keys present in `.env.preview` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OPENOBSERVE_BASIC_AUTH`, `OPENOBSERVE_ROOT_PASSWORD`) were overwritten.

Code trace across `Makefile` (lines 363–385, 449–516, 566–636), `scripts/reconcile_preview_settings.py` (lines 215–290), and `scripts/clone.sh` (lines 295–297) identified four compounding bugs:
1. `Makefile` prebuilt `start` (`MODE=preview`, line 364) pipes `.env.preview` into `reconcile_preview_settings.py --dotenv-stdin 2>/dev/null`, which reads `SRC_SECRET_KEY` only from the container's `os.environ` (where it is never injected), hides stderr, and never force-recreates `web` or `worker` after DB mutations.
2. `Makefile` `preview-reconcile` (line 473) defaults `SKIP_CLONE` to `1` (`${SKIP_CLONE:-1}`), skipping `SRC_LOC` lookups on standalone runs, and invokes host `python3` (lines 490 and 505), breaking host-Python-free prebuilt deployments.
3. `Makefile` `preview-reconcile` (lines 491, 515) hardcodes `APP_VERSION=${APP_VERSION:-preview}` and `monitoring-reset-auth` (line 634) passes no `APP_VERSION` override, causing tagged prebuilt hosts (e.g., `1.1.2`) with stale `.env.preview` `APP_VERSION` entries (e.g., `0.8.4`) to fail pull or downgrade containers on `--force-recreate`.
4. `scripts/reconcile_preview_settings.py` (lines 280–283) prints a green `✅` summary even when undecryptable rows remain, and `scripts/clone.sh` (line 296) omits `SRC_LOC`, `SRC_NAME`, and `SRC_HOST` from its next-step instructions.

## Goals / Non-Goals

**Goals:**
- Propagate `SRC_SECRET_KEY` (direct or read from `SRC_LOC`/`SRC_NAME`/optional `SRC_HOST`) into `reconcile_preview_settings.py --dotenv-stdin` via stdin without leaking secrets into disk, `/proc/<pid>/cmdline` `argv`, container `Config.Env`, or logs.
- Preserve host-Python/Node independence (`tests/bash/test_makefile_prebuilt.bats`) in both `make start preview prebuilt` and `make preview-reconcile`.
- Preserve running container image tags (e.g., `1.1.2` vs `preview`) across `preview-reconcile` and `monitoring-reset-auth` container recreations.
- Surface partial reconciliation visibly (`⚠️` + `preserved undecryptable: N`) and provide exact runnable recovery flags from `scripts/clone.sh`.

**Non-Goals:**
- **Zero-Trust filesystem boundary:** Never auto-discover or read implicit host paths (such as `/opt/iqoqo`) when neither `SRC_SECRET_KEY` nor `SRC_LOC` is explicitly supplied by the operator or wrapper.
- Changing `InstanceSettings` database schema, Fernet envelope format, FRBR models, or Alembic migrations.

## Decisions

### Decision 1: Framed Stdin Header (`__IQOQO_SRC_SECRET_KEY__=`) via Bash Builtin `printf`

- **Selected:** Extend `reconcile_preview_settings.py --dotenv-stdin` to check whether the first line of stdin begins with `__IQOQO_SRC_SECRET_KEY__=`. If present, pop that line before calling `parse_env_text()`, extract the source secret key (falling back to `os.environ.get("SRC_SECRET_KEY", "")` when no header is supplied), and never pass the key into `dst_env` or `InstanceSettings`. Callers stream `{ printf '__IQOQO_SRC_SECRET_KEY__=%s\n' "$$src_secret"; cat "<env-file>"; }` into `docker compose ... exec -T web`. Because `printf` is a bash builtin (`SHELL := /bin/bash`), the key never appears in `ps` / `/proc/<pid>/cmdline`, never touches `/tmp`, never enters container `env`, and requires zero host `python3`.
- **Alternatives Considered:**
  - *Pass `-e SRC_SECRET_KEY=...` to `docker compose exec`:* Rejected because `docker compose exec -e` exposes secrets in container process environments and `docker` invocation metadata.
  - *Keep host `python3` JSON builder (`SRC_SECRET_KEY=... python3 -c ...`):* Rejected because it violates the host-Python-free prebuilt contract.
  - *Write temporary JSON/env file into mounted volume:* Rejected because it persists source `SECRET_KEY` on disk.

### Decision 2: `SKIP_CLONE` Default `0` (`${SKIP_CLONE:-0}`) in `preview-reconcile` and `start` Prebuilt Preview

- **Selected:** Change the `SKIP_CLONE` guard from `${SKIP_CLONE:-1}` to `${SKIP_CLONE:-0}` when `SRC_LOC` is non-empty (and no explicit `SRC_SECRET_KEY` was already supplied). Explicit `SRC_LOC=/opt/iqoqo make preview-reconcile` now reads source `SECRET_KEY` automatically, `scripts/iqopretest.sh --skip-clone` (`SKIP_CLONE=1`) still suppresses source SSH/file reads, and omitting both `SRC_SECRET_KEY` and `SRC_LOC` still performs zero filesystem/SSH access (Zero-Trust).
- **Alternatives Considered:**
  - *Require operators to always pass `SKIP_CLONE=0` manually:* Rejected because intuitive invocations like `SRC_LOC=/opt/iqoqo make preview-reconcile` silently skipped re-encryption.

### Decision 3: Running Container Image Tag Resolution for `APP_VERSION`

- **Selected:** Resolve effective `APP_VERSION` in `preview-reconcile` and `monitoring-reset-auth` in strict order:
  1. Explicit `APP_VERSION` provided by caller (command-line Make variable or exported non-empty override outside stale `.env.preview` interpolation).
  2. Tag of the currently running `web` container image inspected via `docker compose ... ps -q web` + `docker inspect --format '{{.Config.Image}}'`: strip any `@sha256:...` digest, inspect the substring after the last `/`, and extract the tag after `:` if present (safely avoiding registry port `host:5000/repo` mis-parsing).
  3. Fallback to `$(PREBUILT_TAG)` (from `package.json` / `pyproject.toml`), never hardcoded `preview`.
- **Alternatives Considered:**
  - *Keep `APP_VERSION=${APP_VERSION:-preview}`:* Rejected because prebuilt hosts running tagged GHCR releases (`1.1.2`) fail or pull the wrong image on `--force-recreate`.
  - *Read `APP_VERSION` directly from `.env.preview`:* Rejected because `.env.preview` frequently retains stale version strings (observed `0.8.4` on a `1.1.2` host).

### Decision 4: Container-Executed `preview-reconcile` and Post-Reconcile `web`/`worker` Recreate

- **Selected:** Switch `preview-reconcile` RUM provisioning to `docker compose ... exec -T web env PYTHONPATH=/usr/src/app python3 /usr/src/app/scripts/provision_rum_token.py --mgmt-host openobserve` (matching the prebuilt `start` branch, removing host `python3` dependency). In `make start preview prebuilt`, remove `2>/dev/null` from `reconcile_preview_settings.py` so reconciliation status/warnings remain visible in deploy logs, and run `docker compose ... up -d --force-recreate --no-deps web worker` after reconciliation so in-memory caches/workers reflect updated DB settings and admin credentials.

### Decision 5: Honest Partial-Reconciliation Summary & Complete `clone.sh` Hint

- **Selected:** Update `scripts/reconcile_preview_settings.py` stdout summary to print `⚠️ Encrypted settings partially reconciled (re-encrypted: ..., overridden from env: ..., cleared stale: ..., preserved undecryptable: N)` whenever `preserved_undecryptable` is non-empty, retaining `✅ Encrypted settings reconciled (...)` only when `preserved_undecryptable` is empty. Update `scripts/clone.sh` to echo exact `SRC_LOC`, `SRC_NAME`, optional `SRC_HOST`, and `SKIP_CLONE=0`.

## Risks / Trade-offs

- **[Risk] Running `web` container image uses digest-only reference (`repo@sha256:...`) without `:tag`** → **Mitigation:** Strip digest only after checking for `:tag` on the repository path segment; when no explicit tag segment exists after the last `/`, fall back cleanly to `$(PREBUILT_TAG)`.
- **[Risk] `SRC_SECRET_KEY` lookup via SSH (`SRC_HOST`) fails transiently or lacks permissions** → **Mitigation:** Keep existing non-destructive fallback: `src_secret` resolves empty, undecryptable rows are preserved rather than deleted, and partial-reconcile `⚠️` output directs the operator to re-run with `SRC_SECRET_KEY` / `SRC_LOC`.
- **[Risk] `make start preview prebuilt` runs before `web` finishes initial boot or migration** → **Mitigation:** Wait/retry cleanly or log stderr visibly (removing `2>/dev/null`) rather than failing silently, and test dry-run/mock invocations under poisoned host `python`/`python3`/`node`/`npm` in `tests/bash/test_makefile_prebuilt.bats`.
