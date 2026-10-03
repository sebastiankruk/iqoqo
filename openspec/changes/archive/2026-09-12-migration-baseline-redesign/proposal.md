## Why

Consolidating 55 historical migrations directly into a single `v0_7_18_baseline` caused legitimate production upgrades from v0.7.17 (`f65648a6aaf4`) to fail: stamping `v0_7_18_baseline` bypassed DDL execution, leaving new 0.7.18 schema additions (e.g. `auth.token_blocklist.expires_at`, `config` schema for `instance_settings`, check constraints) unapplied and breaking authentication. By anchoring the consolidated baseline at `v0_7_17_baseline` (the exact canonical 0.7.17 state) and layering 0.7.18 schema changes as an incremental `v0_7_18_fixes` migration on top, upgrades from 0.7.17 production stamp the baseline and naturally execute standard DDL migrations without ad-hoc scripts.

## What Changes

- Consolidate historical migrations up to 0.7.17 into a single baseline migration `v0_7_17_baseline.py` (`down_revision = None`).
- Add incremental migration `v0_7_18_fixes.py` (`down_revision = "v0_7_17_baseline"`) containing all 0.7.18 schema updates:
  - Add `auth.token_blocklist.expires_at` column and index.
  - Move `catalog.instance_settings` to `config.instance_settings`.
  - Add missing CheckConstraints (`ck_items_status`, `ck_items_collection_status`, `ck_user_work_intents_status`, `ck_users_visibility`, `ck_loan_requests_status`).
  - Set `ondelete="SET NULL"` on `inventory.user_collections.parent_id`.
- Update migration bridge in `migrations/env.py`, `scripts/fix_alembic.py`, and `run.sh` to stamp `v0_7_17_baseline` when detecting 0.7.17 production head `f65648a6aaf4`.
- Revert ad-hoc schema patches in `scripts/clone.sh` and `scripts/fix_alembic.py`, returning full DDL orchestration to Alembic.
- Update automated tests in `tests/test_migration.py` to assert the two-stage DAG: `None -> v0_7_17_baseline -> v0_7_18_fixes`.

## Capabilities

### Modified Capabilities
- `database-upgrade`: Add requirement for linear Alembic migration baseline bridging and two-stage DAG execution from v0.7.17 production to v0.7.18.

## Impact

- Database migration DAG: `v0_7_17_baseline` -> `v0_7_18_fixes`.
- Migration bridge in `migrations/env.py` and `run.sh`.
- Deployment and cloning scripts (`scripts/fix_alembic.py`, `scripts/clone.sh`).
- Backend test suite `tests/test_migration.py`.
