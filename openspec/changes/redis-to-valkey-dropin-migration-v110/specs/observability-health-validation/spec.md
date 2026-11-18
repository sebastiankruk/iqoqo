## ADDED Requirements

### Requirement: Valkey CLI Cache and Queue Diagnostics
The `scripts/iqoqo-status.sh` diagnostic utility SHALL inspect the cache and Celery broker container using `valkey-cli` (rather than `redis-cli`) to verify connectivity (`PING`), Celery queue length (`LLEN celery`), and memory usage (`INFO memory`).

#### Scenario: Running `make status` against a Valkey-backed stack
- **GIVEN** a running stack whose `redis` container runs `valkey/valkey:8-alpine`
- **WHEN** an operator runs `make status` or `scripts/iqoqo-status.sh`
- **THEN** the status probe MUST execute `valkey-cli` inside the container, report `PING` connectivity as passing, display Celery queue depth and Valkey memory usage, and emit zero `redis-cli: not found` errors.
