## Why

Two infrastructure reliability issues affect deployment stability: (1) Alembic migration `e3f891ab45c2` holds row locks across the entire batch update loop, causing contention during large-table upgrades on production databases; (2) backup jobs fail silently when the `${HOME}/.config/rclone` directory doesn't exist in fresh container deployments.

## What Changes

- **Refactor** Alembic migration `e3f891ab45c2` to execute explicit `session.commit()` after each batch update iteration, releasing row locks incrementally instead of holding them for the entire migration
- **Add pre-start check** in `Makefile` or `docker-compose.yml` entrypoint to create `${HOME}/.config/rclone` directory if missing, preventing silent backup job failures
- **Add tests** for migration batch commit behavior and rclone directory pre-flight check

## Capabilities

### New Capabilities

- `rclone-preflight-check`: Pre-start directory creation check for rclone configuration volume

### Modified Capabilities

- `zero-downtime-migrations`: Refactoring batch commit pattern in migration `e3f891ab45c2` to release row locks incrementally

## Impact

- **Files:** `migrations/versions/e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill.py`, `Makefile` or `deploy/docker-entrypoint.sh`
- **Tests:** Migration test with batch commit verification
- **Risk:** High — modifying a deployed migration requires careful testing against both empty and populated databases
- **DevOps:** Pre-start check prevents silent backup failures on fresh deployments
