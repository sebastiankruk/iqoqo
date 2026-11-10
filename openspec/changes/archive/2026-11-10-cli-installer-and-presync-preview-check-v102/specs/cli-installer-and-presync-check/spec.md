## Purpose

Provide a CI-packaged interactive and non-interactive CLI installer for `iqoqo` that prompts for core environment variables, generates cryptographically secure secrets with `0600` file permissions, and runs `iqopresync` preview and production readiness checks.

## ADDED Requirements

### Requirement: Guided `.env` Generation with Zero-Trust Secret Creation
The CLI installer (`scripts/iqoqo_installer.py`) SHALL prompt for core configuration variables (`NEXT_PUBLIC_FRONTEND_URL`, `FEDERATION_BASE_URL`, `ADMIN_EMAIL`, deployment mode `prod | preview | federation_head`, and optional S3 backup settings), automatically generate 256-bit random secrets for `SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and `REDIS_PASSWORD` using Python `secrets.token_urlsafe`, and write the resulting `.env` file with strict `0600` permissions without ever logging plaintext secrets to stdout.

#### Scenario: User runs interactive installer on a fresh host
- **GIVEN** a host directory with `.env.example` and no existing `.env`
- **WHEN** the operator executes `python3 scripts/iqoqo_installer.py` (or `make install-wizard`) and supplies domain and admin email
- **THEN** the installer writes `.env` with `0600` permissions, populates unique cryptographic secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`), sets `FEDERATION_HEAD_MODE=true` when `federation_head` profile is chosen, and masks all secret values in terminal summary output.

#### Scenario: Production overwrite guard
- **GIVEN** an existing `.env` with `FLASK_ENV=production`
- **WHEN** the operator runs `scripts/iqoqo_installer.py --overwrite`
- **THEN** the script requires typed interactive confirmation of the target hostname before backing up and replacing `.env`.

### Requirement: `iqopresync` Pre-Flight & Preview Readiness Verification
The installer SHALL provide a `--presync-check` (`iqopresync`) mode that validates required `.env` keys, secret entropy, Docker/Compose daemon availability, linear single-head Alembic state, `/api/health`, `/api/system/status`, and WebFinger/NodeInfo federation endpoints, exiting with `0` when ready or non-zero with actionable remediation hints.

#### Scenario: Operator runs `iqopresync` against a preview or prod stack
- **GIVEN** a running or staged `iqoqo` stack
- **WHEN** the operator executes `python3 scripts/iqoqo_installer.py --presync-check` (or `make presync-check`)
- **THEN** the tool verifies `.env` completeness, probes `/api/health` and `/.well-known/nodeinfo`, and reports pass/warn/fail diagnostics compatible with `IQOQO_AI_MODE=1`.
