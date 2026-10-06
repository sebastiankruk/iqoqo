## Context

This design implements the required fixes for v0.7.17 to address the blocker deployment issues and high-severity security findings. See proposal.md for motivation and scope.

## Goals / Non-Goals

**Goals:**
- Fix `flask db upgrade` failure on production caused by renamed migration revisions.
- Fix Docker Compose empty volume initialization caused by renamed project namespace.
- Ensure automated rclone backups have read access to the host-mounted configuration file.
- Prevent Allegro OAuth token refresh races under concurrent multi-worker load.
- Secure the `/api/system/status` endpoint.

**Non-Goals:**
- No new features or functional changes are introduced.
- No changes to business logic outside of the required bug fixes.

## Decisions

1. **Alembic Revisions**: We will revert the `revision` and `down_revision` variables inside `migrations/versions/*.py` to their original strings (e.g., `20260330_add_operation_type_to_llm_telemetry`). Renaming files is fine, but the internal Alembic identifiers must remain unchanged to maintain graph consistency with already-migrated production databases.
2. **Docker Compose Project**: Revert `COMPOSE_PROJECT` in `Makefile` (under `MODE=prod`) from `iqoqo-prod` back to `iqoqo`. Modifying the project name cascades into new volume namespaces, stranding existing production data.
3. **rclone Permissions**: Modify `deploy/docker-entrypoint.sh` to check for readability of the mounted `rclone.conf`. Alternatively, we will document that host permissions for `rclone.conf` must be `0640` and group-owned by `10001`. For this fix, a startup check in the entrypoint is the safest programmatic solution.
4. **Allegro Mutex Lock**: We will use Redis distributed locking (`with cache.lock("allegro_refresh_lock", timeout=30)`) inside `app/utils/allegro.py` for token refresh. Inside the lock, the function will re-read the token from the cache/DB to ensure it hasn't already been refreshed by another worker.
5. **System Status Authentication**: Decorate `get_system_status()` in `app/api/system.py` with `@require_auth` to prevent unauthenticated information disclosure.

## Risks / Trade-offs

- **Risk: Lock Contention**: The Redis lock on Allegro token refresh might cause slight request queuing if multiple workers simultaneously hit the expiry boundary. -> *Mitigation*: The lock timeout is short (30s) and token refreshes are fast.
- **Risk: DB Migration File Mismatch**: Reverting internal variables but keeping shorter filenames might confuse some devs. -> *Mitigation*: This is standard practice in Alembic when file names need changing but history must remain intact.
