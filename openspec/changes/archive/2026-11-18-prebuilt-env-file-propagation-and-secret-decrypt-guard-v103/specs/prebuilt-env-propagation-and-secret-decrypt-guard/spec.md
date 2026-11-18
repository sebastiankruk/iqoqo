## ADDED Requirements

### Requirement: Prebuilt Deployments Propagate ENV_FILE

The Makefile prebuilt `start` target SHALL pass `ENV_FILE=$(COMPOSE_ENV_FILE)` to both `docker compose pull` and `up -d`, so `${ENV_FILE:-.env}` in compose resolves to the same file used for interpolation. `web` and `worker` SHALL receive `APP_VERSION` (default `prod`).

#### Scenario: Production env file used by services

- **GIVEN** `COMPOSE_ENV_FILE=.env.prod`
- **WHEN** `make prebuilt prod start` is invoked
- **THEN** both the `pull` and `up -d` commands MUST carry `ENV_FILE=.env.prod`.

#### Scenario: Default unchanged

- **GIVEN** no production env file selected
- **WHEN** a prebuilt target is invoked
- **THEN** `.env` MUST be used.

### Requirement: INSTALL Documentation Uses a Safe Start Path

`docs/INSTALL.md` SHALL NOT present the raw `docker compose -f docker-compose.prebuilt.yml up -d` one-liner without `ENV_FILE`; it SHALL show `make prebuilt prod start` or the required `ENV_FILE` and `--env-file` pair.

#### Scenario: No unsafe one-liner

- **WHEN** `docs/INSTALL.md` is inspected
- **THEN** every prebuilt compose start example MUST either use `make prebuilt prod start` or set `ENV_FILE`.

### Requirement: Status Detects Secret-Key Mismatch

`make status` (`scripts/iqoqo-status.sh`) SHALL probe one encrypted `InstanceSettings` row without printing its value and, on `InvalidToken`, SHALL fail with a remediation hint naming `ENV_FILE` mismatch and `make migrate-secrets`.

#### Scenario: Wrong key detected

- **GIVEN** an encrypted row written under a different `SECRET_KEY`
- **WHEN** `make status` runs
- **THEN** it MUST report failure with the remediation hint.

#### Scenario: No encrypted rows

- **GIVEN** no encrypted rows exist
- **WHEN** `make status` runs
- **THEN** the probe MUST NOT fail.

### Requirement: Undecryptable Secrets Fail Closed

When a stored secret raises `InvalidToken`, `ConfigService.get()` SHALL return unset and log a warning that names the setting but never its value. Stored rows SHALL NOT be modified.

#### Scenario: InvalidToken surfaces as unset

- **GIVEN** an encrypted setting written with a different key
- **WHEN** `ConfigService.get()` reads it
- **THEN** it MUST return unset, log a warning without the secret, and leave the row unchanged.

### Requirement: Startup Env-Drift Detection (Phase 3, confirm before implementing)

On startup, the application SHOULD log one aggregated `ERROR` with the exact remediation command when encrypted rows fail to decrypt, and `docs/CHANGELOG.md` SHALL carry a `1.0.3` upgrade note forbidding the raw compose one-liner on existing deployments and `SECRET_KEY` rotation without `make migrate-secrets`.

#### Scenario: Aggregated drift error

- **GIVEN** several undecryptable rows
- **WHEN** the application starts
- **THEN** exactly one aggregated `ERROR` MUST be logged.
