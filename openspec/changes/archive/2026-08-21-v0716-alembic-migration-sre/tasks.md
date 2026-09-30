## 1. Refactor Alembic Migration Batch Commits

- [x] 1.1 Read current migration `migrations/versions/e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill.py`
- [x] 1.2 Identify the batch update loop and current transaction handling
- [x] 1.3 Refactor to use `op.get_bind()` with explicit `connection.commit()` after each batch iteration
- [x] 1.4 Add idempotency check: skip already-processed rows on re-run
- [x] 1.5 Set configurable batch size (default 500 rows)
- [x] 1.6 Test migration against empty database
- [x] 1.7 Test migration against populated test database

## 2. Add rclone Pre-Start Directory Check

- [x] 2.1 Identify container entrypoint script (`deploy/docker-entrypoint.sh` or equivalent)
- [x] 2.2 Add `mkdir -p ${HOME}/.config/rclone` command before application start
- [x] 2.3 Verify idempotency — safe to run on every container start
- [x] 2.4 Test fresh container deployment without pre-existing rclone directory

## 3. Write Tests

- [x] 3.1 Create pytest test verifying migration batch commit pattern (mock DB with test rows)
- [x] 3.2 Create test verifying migration runs cleanly on empty database
- [x] 3.3 Create BATS or pytest test verifying entrypoint creates rclone directory

## 4. Verification

- [x] 4.1 Run `make format-python`
- [x] 4.2 Run `make lint-python` — verify no errors
- [x] 4.3 Run `flask db upgrade` in test environment
- [x] 4.4 Run `make test-backend` — verify all tests pass
