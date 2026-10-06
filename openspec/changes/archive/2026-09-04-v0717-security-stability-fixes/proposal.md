## Why

This change addresses Critical and High severity issues identified during the v0.7.17 release reviews (Security, QA, SRE). Specifically, it resolves two deployment blockers (Alembic revision lineage break and Docker Compose volume stranding) that would cause production outages, along with several high-priority security issues including unauthenticated status endpoints, rclone permission mismatches, and race conditions in OAuth token refresh. 

## What Changes

- **Alembic Revisions (BLOCKER)**: Revert internal `revision` and `down_revision` string constants in migration files back to their original historical hashes to prevent `flask db upgrade` from crashing on existing databases.
- **Docker Compose Volumes (BLOCKER)**: Revert `COMPOSE_PROJECT` in `Makefile` back to `iqoqo` for prod (or configure explicit volume names) to avoid creating empty DB volumes and stranding existing data.
- **rclone Container Permissions (HIGH)**: Add group-read access or a startup check for `/home/appuser/.config/rclone/rclone.conf` so UID 10001 can successfully read the mounted host backup credentials.
- **Allegro Token Refresh (HIGH)**: Implement a Redis distributed mutex lock in `app/utils/allegro.py` around the token refresh block to prevent race conditions that permanently de-authorize the application.
- **System Status Security (MEDIUM)**: Add `@require_auth` to `/api/system/status` or strip sensitive integration data from unauthenticated requests to prevent information disclosure.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- **Database Migrations**: `migrations/versions/*.py`
- **Infrastructure/Deploy**: `Makefile`, `docker-compose.yml`, `deploy/docker-entrypoint.sh`
- **Backend API**: `app/api/system.py`, `app/utils/allegro.py`
