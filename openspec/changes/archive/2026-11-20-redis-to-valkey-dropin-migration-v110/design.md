## Context

See `proposal.md` for licensing and operational motivation. Currently `docker-compose.yml` uses `image: redis:8-alpine` with a `redis-cli ping` healthcheck, and `scripts/iqoqo-status.sh` invokes `docker exec "$redis_cname" redis-cli ...` for `PING`, `LLEN celery`, and `INFO memory`. All Python clients (`redis-py`, Celery/Kombu, Flask-Limiter) and OTel's Redis receiver operate over standard RESP2/RESP3 wire protocol on `redis://redis:6379`.

## Goals / Non-Goals

**Goals:**
- Swap the container image to `valkey/valkey:8-alpine` (`valkey-server --maxmemory 256mb --maxmemory-policy allkeys-lru`) across Docker Compose without changing `REDIS_URL` or service/container hostnames.
- Replace every `redis-cli` invocation in compose healthchecks and `scripts/iqoqo-status.sh` with `valkey-cli`.
- Document the one-time `redis_data` volume reset in `docs/CHANGELOG.md` and `docs/INSTALL.md`.

**Non-Goals:**
- Renaming `.env` keys (`REDIS_URL`), Docker Compose service names (`redis`), or Python dependencies (`redis-py`).
- Introducing `valkey://` URI schemes (unsupported by Celery/Kombu without custom transport shims).

## Decisions

1. **Preserve `redis` service name and `redis://` scheme:** Keeps `.env`, `.env.prod`, `Makefile` host-port rewrites, and container network aliases 100% backward-compatible on upgrade. Alternative of renaming service to `valkey` would break existing `.env` files across deployments.
2. **Use `valkey/valkey:8-alpine` with `--maxmemory 256mb --maxmemory-policy allkeys-lru`:** Matches iqoqo's ephemeral cache model (PostgreSQL is the sole persistent source of truth) and mirrors `.context/notes/sre/‎Redis to Valkey migration.md`.
3. **Require `valkey-cli` in `scripts/iqoqo-status.sh`:** `valkey/valkey:8-alpine` ships `valkey-cli`; switching from `redis-cli` prevents false-negative failures in `make status`.

## Risks / Trade-offs

- **Persisted RDB snapshot incompatibility on in-place upgrade** → Document stopping stack and removing/flushing `redis_data` volume (`docker volume rm ...`) in `docs/CHANGELOG.md` and `docs/INSTALL.md` upgrade notes; cache & Celery queues are ephemeral and rebuild automatically.
- **BATS script test mocks referencing `redis-cli`** → Audit and update `tests/scripts/` BATS test doubles alongside `scripts/iqoqo-status.sh`.
