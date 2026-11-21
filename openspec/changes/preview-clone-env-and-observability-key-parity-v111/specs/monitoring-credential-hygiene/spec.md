## MODIFIED Requirements

### Requirement: Auto-provisioned persistent credential lifecycle

The system SHALL auto-provision a cryptographically random OpenObserve root password on first instance startup or bootstrap that satisfies OpenObserve `v0.91.5`'s four-class complexity policy (`is_openobserve_password_strong()`: 8–128 characters including lowercase, uppercase, digit, and special characters while excluding shell-significant `\`, `"`, `$`, and `` ` `` via `generate_openobserve_password()`), ensure it is persisted in the active `.env` file (with `0600` permissions) and mirrored in encrypted database `InstanceSettings`, and ensure existing working passwords (including legacy passwords on an existing `openobserve_data:/data` volume) remain untouched on routine startup unless `--enforce-openobserve-password-policy` is explicitly passed during auth-store reset.

#### Scenario: First-time instance startup or missing credentials

- **WHEN** any startup entry point (`run.sh`, `make start`, `make start preview prebuilt`, `make preview-up`, or bootstrap tooling) starts the monitoring stack without `OPENOBSERVE_ROOT_PASSWORD` set in `.env`
- **THEN** a pre-flight utility auto-provisions a four-class random password via `generate_openobserve_password()`, computes the Base64 Basic-Auth token, writes both to the `.env` file with `0600` permissions, and mirrors `OPENOBSERVE_BASIC_AUTH` into encrypted `InstanceSettings`

#### Scenario: Restarting the monitoring stack with existing volume

- **WHEN** the monitoring stack is restarted
- **THEN** the existing credentials from `.env` are passed to OpenObserve and OTel Collector, ensuring OTel Collector continues to authenticate successfully without `401 Unauthorized` errors

#### Scenario: Routine startup preserves existing weak password for live volume compatibility

- **GIVEN** `.env` contains a non-placeholder `OPENOBSERVE_ROOT_PASSWORD` of at least 16 characters that lacks uppercase or special characters and matches an existing `openobserve_data` volume
- **WHEN** `ensure_env_secrets.py` runs without `--enforce-openobserve-password-policy`
- **THEN** the existing `OPENOBSERVE_ROOT_PASSWORD` MUST be preserved unchanged so OpenObserve authentication against the existing volume is not broken

#### Scenario: Auth reset enforces four-class password policy before clearing /data/db

- **GIVEN** `.env` contains a weak `OPENOBSERVE_ROOT_PASSWORD` failing `is_openobserve_password_strong()`
- **WHEN** `ensure_env_secrets.py --enforce-openobserve-password-policy` runs before `/data/db` is cleared during `monitoring-reset-auth`
- **THEN** it MUST regenerate `OPENOBSERVE_ROOT_PASSWORD` with `generate_openobserve_password()`, recompute `OPENOBSERVE_BASIC_AUTH`, write `.env` with mode `0600`, and sync `OPENOBSERVE_BASIC_AUTH` into encrypted `InstanceSettings` when the database is reachable
