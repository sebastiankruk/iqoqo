## MODIFIED Requirements

### Requirement: Prebuilt Deployments Propagate ENV_FILE

The Makefile prebuilt `start` target SHALL pass `ENV_FILE=$(COMPOSE_ENV_FILE)` to both `docker compose pull` and `up -d`, so `${ENV_FILE:-.env}` in compose resolves to the same file used for interpolation, SHALL preserve the default `ghcr.io/sebastiankruk/` `IMAGE_PREFIX` even if the active `.env` file declares an empty `IMAGE_PREFIX=`, and SHALL ensure `web` and `worker` receive `APP_VERSION` (default `prod`). For `preview` prebuilt deployments (`make start preview prebuilt` / `make preview start prebuilt`), the target SHALL additionally align with `make preview-up` / `make preview-reconcile` by tightening env permissions to `0600`, pre-starting `docker-compose.monitoring.yml` before RUM token provisioning when `OTEL_TRACES_EXPORTER != none`, executing secret/OpenObserve/DB reconciliation via container-executed Python (`docker compose ... exec -T web` or `run --rm`) without requiring host `python`, `python3`, `node`, or `npm`, and passing `OPENOBSERVE_RUM_CLIENT_TOKEN`, `OPENOBSERVE_RUM_SITE`, and `OPENOBSERVE_RUM_INSECURE_HTTP` to `frontend`.

#### Scenario: Production env file used by services

- **GIVEN** `COMPOSE_ENV_FILE=.env.prod`
- **WHEN** `make prebuilt prod start` is invoked
- **THEN** both the `pull` and `up -d` commands MUST carry `ENV_FILE=.env.prod`.

#### Scenario: Default unchanged

- **GIVEN** no production env file selected
- **WHEN** a prebuilt target is invoked
- **THEN** `.env` MUST be used.

#### Scenario: Empty IMAGE_PREFIX in env file does not strip GHCR registry prefix

- **GIVEN** `.env.preview` contains `IMAGE_PREFIX=` (empty value) and no explicit `IMAGE_PREFIX` is exported by the caller
- **WHEN** `docker compose -f docker-compose.prebuilt.yml` resolves service image names during `make start preview prebuilt` or `make preview-up`
- **THEN** images MUST resolve with `ghcr.io/sebastiankruk/` (e.g., `ghcr.io/sebastiankruk/iqoqo-backend:<tag>`) rather than an unprefixed local image name.

#### Scenario: Prebuilt preview start reconciles secrets and RUM without requiring host Python or Node

- **GIVEN** a host without `python`, `python3`, `node`, or `npm` on `PATH` and a `.env.preview` file configuring preview origins and `SECRET_KEY`
- **WHEN** `make preview start prebuilt` executes
- **THEN** it MUST complete without invoking host `python`/`python3`/`node`/`npm`, enforce `0600` on `.env.preview`, pre-start monitoring and inject `OPENOBSERVE_RUM_*` into `frontend`, and run container-side `InstanceSettings` / OpenObserve reconciliation against `.env.preview`.

### Requirement: Status Detects Secret-Key Mismatch

`make status` (`scripts/iqoqo-status.sh`) SHALL probe all encrypted `InstanceSettings` rows via `check_encrypted_settings_drift()` without printing any plaintext or ciphertext values and, on `InvalidToken` in any row, SHALL fail reporting the affected key names and a remediation hint naming `ENV_FILE` mismatch, `make preview-reconcile`, and `make migrate-secrets`.

#### Scenario: Wrong key detected

- **GIVEN** an encrypted row written under a different `SECRET_KEY`
- **WHEN** `make status` runs
- **THEN** it MUST report failure with the affected key name(s) and remediation hint.

#### Scenario: No encrypted rows

- **GIVEN** no encrypted rows exist
- **WHEN** `make status` runs
- **THEN** the probe MUST NOT fail.

#### Scenario: Partial secret-key drift across mixed encrypted rows is detected

- **GIVEN** `InstanceSettings` contains two rows encrypted under preview `SECRET_KEY` (such as `OPENOBSERVE_BASIC_AUTH`) and fifteen rows still encrypted under production `SECRET_KEY`
- **WHEN** `make status` runs the `Encrypted settings` check
- **THEN** it MUST evaluate all encrypted rows via `check_encrypted_settings_drift()` and report `fail` listing the fifteen undecryptable keys rather than passing on a single healthy sample row.
