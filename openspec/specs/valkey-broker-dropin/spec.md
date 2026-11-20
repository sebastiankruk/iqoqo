# valkey-broker-dropin Specification

## Purpose
Replace the Redis container image with Valkey 8 as a drop-in cache, rate-limit, and Celery message broker across Docker Compose orchestration and operational diagnostics while maintaining full `redis://` URI and `redis:6379` network compatibility.

## Requirements

### Requirement: Drop-In Valkey Broker and Cache Container Orchestration
The system SHALL run `valkey/valkey:8-alpine` under the existing `redis` Docker Compose service name, container alias (`redis:6379`), and `redis://` URI scheme with `valkey-cli ping` container healthchecks and `allkeys-lru` eviction policy.

#### Scenario: Application services connect to Valkey over existing `redis://` URIs

- **GIVEN** a Docker Compose deployment running `valkey/valkey:8-alpine` on service `redis`
- **WHEN** the Flask API, Celery worker, SSE event subscriber (`iqoqo:events`), Flask-Limiter, and OTel Collector connect using `REDIS_URL=redis://redis:6379/...`
- **THEN** all connections, Celery queues, rate-limiting buckets, and Pub/Sub streams MUST succeed without changing application-level URI schemes or environment variable names.

#### Scenario: Docker container healthcheck uses `valkey-cli`

- **GIVEN** the `redis` service definition in `docker-compose.yml`
- **WHEN** Docker evaluates the container healthcheck
- **THEN** the healthcheck command MUST execute `valkey-cli ping` and report healthy upon receiving `PONG`.

### Requirement: Valkey Upgrade and Volume Reset Documentation
System upgrade documentation SHALL explain how to cleanly reset or flush the `redis_data` volume when upgrading from Redis 8 to Valkey 8 so incompatible persisted RDB snapshots do not block startup.

#### Scenario: Operator upgrades an existing stack from v1.0.x to v1.1.0

- **GIVEN** an instance previously running `redis:8-alpine` with an existing `redis_data` volume
- **WHEN** the operator consults `docs/CHANGELOG.md` and `docs/INSTALL.md` for `v1.1.0`
- **THEN** clear instructions MUST be documented explaining that cache/queue data is ephemeral and how to recreate or flush `redis_data` during cutover.
