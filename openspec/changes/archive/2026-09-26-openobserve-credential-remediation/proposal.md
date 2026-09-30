## Why

Commit `61a7a50` (2026-09-01, branch `fix/0.7.17/multi-candidate-lookup`) hardcoded the OpenObserve default password `SuperSecret!123` and its Base64 Basic-Auth encoding `YWRtaW5AaXFvcW8ubG9jYWw6U3VwZXJTZWNyZXQhMTIz` into 8 tracked files across shell scripts, OTEL collector configs, E2E tests, and documentation. The prior default `supersecret` / `YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=` also persists in `.agents/skills/devops-observability-expert/SKILL.md`.

OpenObserve is an internal-only service, not exposed outside the host. The `release/0.8.1` branches will be squash-merged, so feature-branch history is not a concern — we simply overwrite the files. However, **v0.7.18 PROD** (the current production release) carries the hardcoded values in `run.sh:471`, `scripts/iqoqo-status.sh:292`, and `docs/MONITORING.md`, making them discoverable in the tagged release history.

This must be remediated because:

1. Hardcoded fallback credentials in shell scripts and OTEL configs bypass `.env`-based secret management, violating the project's "Secret Encryption at Rest" policy.
2. Documentation examples encourage copy-paste of real credentials instead of `$VARIABLE` references.
3. The `docker-compose.monitoring.yml` was partially cleaned (password fallback removed), but downstream consumers (`run.sh`, `iqoqo-status.sh`, OTEL configs, E2E test, docs) were not.
4. v0.7.18 PROD tag permanently contains the hardcoded values in Git history.

## What Changes

- **Remove all hardcoded OpenObserve passwords and Base64 auth tokens** from shell scripts (`run.sh`, `scripts/iqoqo-status.sh`), OTEL collector configs (`deploy/otel-collector-local.yaml`, `deploy/otel-collector-prod.yaml`), E2E tests (`openobserve_rum.spec.ts`), documentation (`MONITORING.md`), and AI skill files (`devops-observability-expert/SKILL.md`).
- **Auto-provision and persist OpenObserve credentials across all entry points**: OpenObserve root credentials are tied to the persistent data volume (`openobserve_data:/data`) and cannot be rotated purely in-memory on restart without breaking OTel export and OpenObserve authentication. The system must auto-provision cryptographically random credentials on first run/bootstrap via a pre-flight helper (`scripts/ensure_monitoring_auth.py`), store them in the active `.env` file (like `SECRET_KEY`), and mirror them encrypted into database `InstanceSettings`. This ensures that local dev (`run.sh`), prebuilt preview (`iqopretest`, `make start preview prebuilt`), and production stacks start cleanly without manual `.env` editing or unassigned Docker Compose variable warnings.
- **Enforce fail-closed Docker Compose configuration**: In `docker-compose.monitoring.yml`, replace naked parameter expansion with fail-closed assertions (`:?`) to prevent Docker Compose from silently passing empty string passwords that crash OpenObserve or corrupt telemetry.
- **Update documentation** to explain credential auto-provisioning and secure retrieval — no manual plaintext password management needed.
- **Add a pre-commit / CI secret-scan rule** (`.gitleaks.toml` or equivalent) to prevent future hardcoded credential commits.

## Capabilities

### New Capabilities

- `monitoring-credential-hygiene`: Defines requirements for auto-provisioned, persistent credential management in the observability stack, prohibiting hardcoded fallback passwords and Base64 auth tokens in tracked files while ensuring compatibility with persistent storage volumes and all deployment entry points.

### Modified Capabilities

- `security-and-secrets`: Extends the existing secret management spec to cover monitoring infrastructure credentials (OpenObserve, OTEL collector) under the same security posture.

## Impact

- **Shell scripts**: `run.sh`, `scripts/iqoqo-status.sh` — hardcoded auth fallbacks replaced with auto-generated credentials and DB/cache lookup.
- **OTEL configs**: `deploy/otel-collector-local.yaml`, `deploy/otel-collector-prod.yaml` — hardcoded comments and fallback values removed.
- **E2E tests**: `frontend/__tests__/e2e/openobserve_rum.spec.ts` — auth pulled from auto-generated credentials or test fixtures.
- **Documentation**: `docs/MONITORING.md`, `docs/CHANGELOG.md` — credential examples replaced with explanation of auto-generation.
- **AI skill**: `.agents/skills/devops-observability-expert/SKILL.md` — old credentials removed, updated to reference DB/cache lookup.
- **CI/CD**: New `.gitleaks.toml` secret scanning config added.
- **v0.7.18 PROD**: Hardcoded values remain in tagged release history; this is an internal-only service so exposure is limited to the host.
