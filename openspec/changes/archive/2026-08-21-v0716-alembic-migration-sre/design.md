## Context

Migration `e3f891ab45c2` performs ETL backfill of relational FRBR columns from JSONB blobs. The current batch loop holds row locks for the entire operation, causing lock contention on production PostgreSQL during upgrades. Separately, fresh container deployments fail silently when `${HOME}/.config/rclone` directory is missing, preventing backup job initialization.

## Goals / Non-Goals

**Goals:**

- Refactor migration `e3f891ab45c2` to commit after each batch iteration, releasing row locks incrementally
- Add pre-start directory creation for `${HOME}/.config/rclone` in the container entrypoint
- Verify migration works correctly with both empty and populated databases
- Ensure rclone directory check is idempotent (safe to run on every start)

**Non-Goals:**

- Rewriting the migration from scratch
- Changing the ETL backfill logic itself
- Adding rclone configuration management

## Decisions

### Decision 1: Batch commit within Alembic `op.execute()` context
**Choice:** Use `op.get_bind().execute()` with explicit `connection.commit()` after each batch, wrapped in Alembic's `batch_alter_table` context.
**Rationale:** Alembic's default transaction wrapping can be overridden safely for data migrations using `op.get_bind()` to access the raw connection.
**Alternative considered:** Using `autocommit=True` — rejected because it removes rollback capability entirely.

### Decision 2: Entrypoint script for rclone directory check
**Choice:** Add `mkdir -p ${HOME}/.config/rclone` to `deploy/docker-entrypoint.sh` before any rclone operations.
**Rationale:** Entrypoint is the canonical location for pre-start checks. `mkdir -p` is idempotent.
**Alternative considered:** Makefile target — rejected because it wouldn't run in production Docker deployments.

## Risks / Trade-offs

- **Risk:** Modifying a deployed migration could cause issues if re-run on databases already migrated → **Mitigation:** Add idempotency checks (skip if column already populated)
- **Risk:** Batch commits make partial migration possible (crash mid-batch) → **Mitigation:** Each batch is self-contained; re-running processes remaining rows
