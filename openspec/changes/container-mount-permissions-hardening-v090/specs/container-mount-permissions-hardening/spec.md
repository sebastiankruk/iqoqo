## ADDED Requirements

### Requirement: Container Entrypoint Volume Writability Assertion
The system container entrypoint script (`deploy/docker-entrypoint.sh`) MUST verify writability for all host bind-mounted asset, cache, and data directories (`app/static/covers`, `app/static/gallery`, `exports`, and `data`) before executing application server processes. If any directory is not writable by the executing unprivileged container user (`appuser`, UID 10001), the entrypoint MUST log an error detailing which paths failed, output host remediation instructions, and terminate execution immediately with a non-zero exit code.

#### Scenario: Container starts with writable mounted volumes
- **WHEN** the backend application container initializes
- **AND** all mounted directories (`app/static/covers`, `app/static/gallery`, `exports`, and `data`) are writable by UID 10001
- **THEN** the entrypoint logs successful verification and continues execution without aborting

#### Scenario: Container starts with unwritable mounted volumes
- **WHEN** the backend application container initializes
- **AND** one or more mounted directories are not writable by the non-root container user
- **THEN** the entrypoint logs an error listing each unwritable directory
- **THEN** the entrypoint prints recommended host remediation commands (`chmod -R a+rwX <dirs>`) and exits with a non-zero exit code before starting Gunicorn or Celery

### Requirement: Orchestration Startup Permission Preparation
The orchestration automation in `Makefile` MUST ensure that all host directories mounted into containers exist and possess permissive read/write access prior to launching Docker Compose stacks.

#### Scenario: Orchestration startup ensures mount directory permissions
- **WHEN** an operator invokes `make start`, `make preview-up`, or equivalent container startup targets
- **THEN** the orchestration prerequisite (`ensure-mount-perms`) creates required host paths if missing
- **THEN** the prerequisite grants read, write, and execute permissions (`chmod -R a+rwX`) on host mount directories before invoking `docker compose up`

### Requirement: Operational Diagnostic Mount Writability Verification
The diagnostic inspection script (`scripts/iqoqo-status.sh`) MUST test container-level write permissions for bind-mounted static directories when inspecting active container stacks.

#### Scenario: Diagnostic check succeeds when container mounts are writable
- **WHEN** `scripts/iqoqo-status.sh` is executed against an active container stack (`STACK=prod` or `STACK=preview`)
- **AND** the web container user can write to mounted directories
- **THEN** the status check marks volume mount writability as passing

#### Scenario: Diagnostic check warns when container mounts are read-only or unwritable
- **WHEN** `scripts/iqoqo-status.sh` is executed against an active container stack
- **AND** a mounted directory cannot be written by the container user
- **THEN** the status check outputs an error diagnostic highlighting the unwritable path and exits with an operational warning
