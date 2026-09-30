## Context

Commit `61a7a50` (2026-09-01) introduced `SuperSecret!123` and its Base64 encoding as hardcoded fallbacks across 8 files. The prior default `supersecret` also persists in the DevOps skill file. See proposal.md for full motivation and file inventory.

OpenObserve is an internal-only service, not exposed outside the host. The `release/0.8.1` branches will be squash-merged into `main`, so feature-branch history containing the hardcoded creds will not persist in the mainline. However, v0.7.18 PROD (current production tag) carries the hardcoded values in `run.sh`, `iqoqo-status.sh`, and `MONITORING.md`.

The `docker-compose.monitoring.yml` was partially remediated in a later commit (password fallback removed from `ZO_ROOT_USER_PASSWORD` and `OPENOBSERVE_BASIC_AUTH` lines), but 6 downstream consumers still carry the hardcoded values:

| File | What's hardcoded |
|---|---|
| `run.sh:471` | Base64 auth fallback literal |
| `scripts/iqoqo-status.sh:292` | Base64 auth fallback literal |
| `deploy/otel-collector-local.yaml:56-57` | Password in comment |
| `deploy/otel-collector-prod.yaml:99-100` | Password in comment |
| `frontend/__tests__/e2e/openobserve_rum.spec.ts:46` | Base64 auth literal |
| `docs/MONITORING.md:55,148,161` | Password + Base64 in docs |
| `.agents/skills/devops-observability-expert/SKILL.md` | Old `supersecret` + Base64 |
| `docs/CHANGELOG.md:87` | Password mentioned in changelog entry |

## Goals / Non-Goals

**Goals:**

1. Remove every hardcoded OpenObserve credential from all tracked files on `release/0.8.1`.
2. Auto-generate OpenObserve credentials at each monitoring startup and store the derived auth token in the application DB or cache.
3. Enable SRE tools and status scripts to retrieve credentials from DB/cache without file-based storage.
4. Add CI gitleaks scanning to prevent recurrence.
5. Update all documentation to explain auto-generation instead of manual credential management.

**Non-Goals:**

- Rewriting Git history (force-push / BFG) — the `release/0.8.1` branches will be squash-merged (overwriting history), and v0.7.18 PROD exposure is limited to an internal-only service.
- Changing the OpenObserve authentication mechanism itself (e.g., switching to OIDC).
- Credential rotation documentation — credentials are ephemeral and regenerated at each startup, so rotation is not applicable.

## Decisions

### Decision 1: Auto-provisioned, persistent credentials per instance volume

**Choice:** Provide a pre-flight provisioning utility (`scripts/ensure_monitoring_auth.py`) that checks if `OPENOBSERVE_ROOT_PASSWORD` and `OPENOBSERVE_BASIC_AUTH` are set in the target `.env` file. If missing, it generates a cryptographically random password via `secrets.token_urlsafe(32)`, computes the Base64 Basic-Auth token (`base64(OPENOBSERVE_ROOT_USER:OPENOBSERVE_ROOT_PASSWORD)`), and writes them to the `.env` file (matching the existing pattern used by `run.sh` for `SECRET_KEY` and `JWT_SECRET_KEY`). It also mirrors the credentials into encrypted `InstanceSettings` in the application DB.

**Rationale:** Empirical testing of OpenObserve reveals that it hashes `ZO_ROOT_USER_PASSWORD` on volume creation and **ignores** changes to `ZO_ROOT_USER_PASSWORD` on container restarts if the volume already exists. Generating a new ephemeral password on every restart causes OpenObserve to reject OTel Collector and SRE status queries with `HTTP 401 Unauthorized`. Credentials must be stable per data volume. Auto-provisioning into `.env` on first boot avoids requiring manual setup while maintaining full compatibility with OpenObserve's storage engine.

### Decision 2: Fail-closed Compose definition with universal pre-flight integration

**Choice:** In `docker-compose.monitoring.yml`, declare `${OPENOBSERVE_ROOT_PASSWORD:?OPENOBSERVE_ROOT_PASSWORD must be set in environment or .env}` and `${OPENOBSERVE_BASIC_AUTH:?OPENOBSERVE_BASIC_AUTH must be set in environment or .env}`. Wire the pre-flight provisioning hook into `Makefile` (`start` and `prebuilt` targets) and `run.sh` before Docker Compose is executed.

**Rationale:** Naked variable interpolation without fallback defaults to empty strings (`""`), causing Docker Compose to emit warnings and OpenObserve to crash on fresh start with a broken channel error. Fail-closed syntax prevents silent startup failures, while pre-flight integration ensures the variables are always present in the environment/`.env` before Compose runs across all entry points (`run.sh`, `make start`, `make start preview prebuilt`, and deployment scripts).

### Decision 3: OTEL collector configs use env var substitution

**Choice:** Remove hardcoded password values from YAML comments in `deploy/otel-collector-*.yaml`. The actual `Authorization` header is configured via `Authorization: "Basic ${OPENOBSERVE_BASIC_AUTH}"` in the YAML body. The pre-flight provisioning ensures `OPENOBSERVE_BASIC_AUTH` is populated in the environment.

### Decision 4: E2E test reads auth from env or DB

**Choice:** Replace the hardcoded `basicAuth` constant in `openobserve_rum.spec.ts` with a lookup from `process.env.OPENOBSERVE_BASIC_AUTH` (populated by the test harness from the auto-generated value). Add a `test.skip` guard if the value is unavailable.

**Rationale:** E2E tests already run with env vars injected by the test harness. The `seed_e2e.py` script can be extended to export the auto-generated auth.

### Decision 5: Gitleaks CI integration

**Choice:** Add `.gitleaks.toml` with rules targeting the known Base64 prefixes and password literals, plus a GitHub Actions step in `quality.yml` that runs `gitleaks detect --config .gitleaks.toml` on every PR.

**Alternative considered:** `trufflehog` — heavier, requires API key for full features. Gitleaks is lightweight, open-source, and already widely adopted.

### Decision 6: Changelog mentions are acceptable

**Choice:** The `docs/CHANGELOG.md:87` line mentioning "Removed hardcoded `SuperSecret!123` fallback" is a historical record of the fix itself and does not constitute a credential leak. It will be left as-is.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Status script cannot reach DB when Flask is not running | Falls back to `$OPENOBSERVE_BASIC_AUTH` env var if set, or skips check with informational message |
| E2E test failures if auto-generated auth not injected | `seed_e2e.py` exports the value; `test.skip` guard if unavailable |
| v0.7.18 PROD Git history contains the hardcoded values | Internal-only service, not exposed outside host; upgrading to v0.8.1 with auto-generation eliminates the issue going forward |

## Migration Plan

1. Create branch `fix/0.8.1/openobserve-cred-remediation` from `release/0.8.1`.
2. Apply all file changes (see tasks.md).
3. Run `make lint` and `make test` locally.
4. Push and open PR against `release/0.8.1` (squash-merge will overwrite all feature-branch history).
5. After merge, notify contributors to pull latest — no `.env` changes needed, credentials are now auto-generated.
