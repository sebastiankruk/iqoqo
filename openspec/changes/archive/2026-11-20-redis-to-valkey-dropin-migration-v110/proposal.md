## Why

Redis 7.2+ licensing shifts (RSALv2/SSPL) diverge from iqoqo's open-source AGPL sovereignty principles. Valkey 8 (BSD-3-Clause, Linux Foundation) offers full wire-protocol parity (`RESP2`/`RESP3`), lower lock contention, and drop-in compatibility across Celery, Flask-Limiter, SSE Pub/Sub (`iqoqo:events`), and OpenTelemetry scrapers with zero application code changes.

## What Changes

- Replace the `redis` service image in `docker-compose.yml` (and any non-test compose overlays referencing `redis:8-alpine`) with `valkey/valkey:8-alpine` running `valkey-server --maxmemory 256mb --maxmemory-policy allkeys-lru`.
- Retain the Docker Compose service name `redis`, internal host alias `redis:6379`, `redis_data` volume name, and `redis://` URI scheme across `.env.example`, Flask, Celery, and `RATELIMIT_STORAGE_URI` so Python clients (`redis-py`, Kombu, Flask-Limiter) require zero changes.
- Update container healthchecks (`docker-compose.yml`), host operational scripts (`scripts/iqoqo-status.sh`), and `Makefile` targets from `redis-cli` to `valkey-cli`.
- Document the Valkey cutover and one-time `redis_data` volume flush/recreate step in `docs/CHANGELOG.md` and `docs/INSTALL.md`.

## Capabilities

### New Capabilities
- `valkey-broker-dropin`: Drop-in replacement of Redis with Valkey 8 across Docker Compose orchestration, `valkey-cli` health/status probes, and upgrade documentation while preserving `redis://` URIs and `redis:6379` service naming.

### Modified Capabilities
- `observability-health-validation`: Update `scripts/iqoqo-status.sh` Redis/cache diagnostic probes to execute `valkey-cli` inside the `redis` container rather than `redis-cli`.

## Impact

- **Orchestration & Scripts**: `docker-compose.yml`, `scripts/iqoqo-status.sh`, `Makefile`, `.env.example`.
- **Documentation**: `docs/CHANGELOG.md`, `docs/INSTALL.md`, `.context/notes/sre/‎Redis to Valkey migration.md`.
- **Tests**: `tests/scripts/` (BATS tests for `iqoqo-status.sh`), Redis/Valkey connectivity smoke check.
