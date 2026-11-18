## 1. Docker Compose & Environment Cutover

- [ ] 1.1 Update the `redis` service in `docker-compose.yml` from `redis:8-alpine` to `valkey/valkey:8-alpine` with `command: valkey-server --maxmemory 256mb --maxmemory-policy allkeys-lru` and `healthcheck` `["CMD", "valkey-cli", "ping"]` while retaining the `redis` service name, `redis_data` volume, and `redis://` URI scheme; verify compose config via `docker compose config --quiet`
- [ ] 1.2 Audit all `docker-compose*.yml`, `.env.example`, and `Makefile` targets for any `redis-cli` or `redis:8-alpine` references (retaining `redis://` URIs and `redis:6379` host aliases) and update any CLI calls to `valkey-cli`; verify via `IQOQO_AI_MODE=1 make lint`

## 2. Operational Scripts & BATS Tests

- [ ] 2.1 Update `scripts/iqoqo-status.sh` to invoke `valkey-cli` (instead of `redis-cli`) for `PING`, `LLEN celery`, and `INFO memory` diagnostics, update mock stubs in `tests/bash/iqoqo_status.bats`, and verify via `bats tests/bash/iqoqo_status.bats tests/bash/scripts_syntax.bats`

## 3. Upgrade Documentation & Verification

- [ ] 3.1 Document the Redis-to-Valkey migration and one-time `redis_data` volume flush/recreate procedure in `docs/CHANGELOG.md` and `docs/INSTALL.md`, and verify Markdown formatting via `npx markdownlint-cli2 "docs/CHANGELOG.md" "docs/INSTALL.md"`
- [ ] 3.2 Verify Valkey drop-in connectivity across Celery/Redis clients and healthchecks locally (`IQOQO_AI_MODE=1 make test-parallel` and `bats tests/bash/iqoqo_status.bats`)
