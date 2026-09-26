# monitoring-credential-hygiene Specification

## Purpose

Ensures that the observability stack (OpenObserve, OpenTelemetry Collector) never stores authentication credentials as hardcoded literals in version-controlled files, using auto-generated ephemeral credentials at each startup with runtime-only storage in the application database or cache.

## Requirements

### Requirement: No hardcoded monitoring credentials in tracked files
The system SHALL NOT contain any hardcoded OpenObserve passwords, Base64-encoded Basic-Auth tokens, or other monitoring infrastructure credentials in any version-controlled file (shell scripts, YAML configs, TypeScript tests, Markdown documentation, or AI skill files).

#### Scenario: Scanning codebase for literal credentials

- **WHEN** a CI pipeline or pre-commit hook scans tracked files for patterns matching `SuperSecret`, `supersecret`, or the known Base64 encodings `YWRtaW5AaXFvcW8ubG9jYWw6U3VwZXJTZWNyZXQhMTIz` and `YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=`
- **THEN** zero matches are found outside of test fixtures that explicitly test the secret-scanning rule itself

#### Scenario: Reviewing OTEL collector configuration

- **WHEN** a developer inspects `deploy/otel-collector-local.yaml` or `deploy/otel-collector-prod.yaml`
- **THEN** the Authorization header value is derived from auto-generated credentials, not from a literal string

### Requirement: Auto-provisioned persistent credential lifecycle
The system SHALL auto-provision a cryptographically random OpenObserve root password on first instance startup or bootstrap, ensure it is persisted in the active `.env` file and mirrored in encrypted database `InstanceSettings`, and ensure it remains stable across container restarts to maintain compatibility with OpenObserve's persistent storage volume (`openobserve_data:/data`).

#### Scenario: First-time instance startup or missing credentials

- **WHEN** any startup entry point (`run.sh`, `make start`, `make start preview prebuilt`, or bootstrap tooling) starts the monitoring stack without `OPENOBSERVE_ROOT_PASSWORD` set in `.env`
- **THEN** a pre-flight utility auto-provisions a random password (via `secrets.token_urlsafe(32)`), computes the Base64 Basic-Auth token, writes both to the `.env` file, and mirrors them into encrypted `InstanceSettings`

#### Scenario: Restarting the monitoring stack with existing volume

- **WHEN** the monitoring stack is restarted
- **THEN** the existing credentials from `.env` are passed to OpenObserve and OTel Collector, ensuring OTel Collector continues to authenticate successfully without `401 Unauthorized` errors

### Requirement: Fail-closed Docker Compose parameter validation
The system SHALL enforce fail-closed variable validation in `docker-compose.monitoring.yml` (`:?`) so that Docker Compose rejects startup with an explicit descriptive error if monitoring credentials are not provided in the environment or `.env`, prohibiting blank string fallbacks that crash OpenObserve or corrupt telemetry.

#### Scenario: Direct Docker Compose execution with missing credentials

- **WHEN** an operator runs `docker compose -f docker-compose.monitoring.yml up` or `docker compose -f docker-compose.prebuilt.yml up` without `OPENOBSERVE_ROOT_PASSWORD` or `OPENOBSERVE_BASIC_AUTH` set in the environment or `.env`
- **THEN** Docker Compose halts immediately with a clear error indicating the missing variable, rather than emitting unassigned variable warnings and passing blank strings

### Requirement: Credential accessibility via DB or environment
The system SHALL mirror the auto-provisioned OpenObserve Basic-Auth token in `InstanceSettings` (encrypted at rest via Fernet keyed from `SECRET_KEY`) and in the active `.env` file so that SRE tools, status scripts, and AI skill agents can query OpenObserve without reading plaintext secrets from version-controlled files.

#### Scenario: SRE status script querying OpenObserve

- **WHEN** `scripts/iqoqo-status.sh` or an AI agent needs to check OpenObserve health or query telemetry data
- **THEN** it retrieves the current Basic-Auth token from the environment, active `.env`, or decrypted `InstanceSettings` in DB and uses it for the API call

#### Scenario: Application not running when status check executes

- **WHEN** the Flask application is not running but the status script needs to check OpenObserve
- **THEN** the script falls back to reading `OPENOBSERVE_BASIC_AUTH` from `.env` or environment, or skips the OpenObserve health check with an informational message if unconfigured

### Requirement: CI secret scanning gate
The system SHALL include a CI-level secret scanning configuration (e.g., `.gitleaks.toml`) that flags commits introducing hardcoded monitoring credentials and blocks the merge.

#### Scenario: Developer commits a hardcoded OpenObserve Base64 token

- **WHEN** a developer pushes a commit containing the literal string `YWRtaW5AaXFvcW8ubG9jYWw6` (the invariant Base64 prefix for `admin@iqoqo.local:`)
- **THEN** the CI secret scanning job fails and the PR cannot be merged

### Requirement: Documentation explains auto-generation
All monitoring documentation SHALL explain that OpenObserve credentials are auto-generated at startup and accessible via the application database or cache, and SHALL NOT contain example values that are real or default credentials.

#### Scenario: Reading MONITORING.md curl examples

- **WHEN** a developer reads the curl examples in `docs/MONITORING.md`
- **THEN** the Authorization header uses a placeholder like `<auto-generated — retrieve via DB or iqoqo-status.sh>` rather than a real encoded value
