## 1. Alembic Revisions Fix (Blocker)

- [x] 1.1 In `migrations/versions/20260330_llm_telemetry_op_type.py`, revert the `revision` string to `"20260330_add_operation_type_to_llm_telemetry"` and verify `flask db upgrade` parses it correctly.
- [x] 1.2 In `migrations/versions/20260331_frbr_catalog_schema.py`, revert the `revision` string to `"20260331_move_frbr_to_catalog_schema"` and verify correct linkage.
- [x] 1.3 In `migrations/versions/20260331_merge_token_telemetry.py`, revert the `revision` string to `"20260331_merge_token_and_telemetry_branches"`.
- [x] 1.4 Update any `down_revision` pointers in these files that might have been changed to the shorter names, reverting them to the original hashes, and verify `flask db history` runs without errors.

## 2. Docker Compose Project Fix (Blocker)

- [x] 2.1 In `Makefile`, revert `COMPOSE_PROJECT` for `MODE=prod` back to `iqoqo` (from `iqoqo-prod`) and verify the change by running `make prod config` (or similar) to ensure the volume names match the `iqoqo_*` prefix.

## 3. High-Priority Security Fixes

- [x] 3.1 In `deploy/docker-entrypoint.sh`, add a startup check to ensure `/home/appuser/.config/rclone/rclone.conf` is readable by the current user (UID 10001), logging a warning if not. Verify by testing the entrypoint script locally.
- [x] 3.2 In `app/utils/allegro.py`, wrap the token refresh block with `with cache.lock("allegro_refresh_lock", timeout=30):` and re-check the token's age inside the lock. Verify by running the allegro tests.
- [x] 3.3 In `app/api/system.py`, add the `@require_auth` decorator to `get_system_status()` (or strip sensitive info if unauthenticated) and verify the endpoint returns 401 for unauthorized requests in `tests/test_system.py` or equivalent.
