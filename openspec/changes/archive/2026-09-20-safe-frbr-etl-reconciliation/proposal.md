## Why

The 0.8.0 FRBR ETL deletes duplicate Work and Manifestation rows after reparenting only a subset of child records. Cascades can remove WorkPart, expansion, contribution, intent, image, feedback, note, and other related data, while the JSON snapshot does not contain enough information to restore it. Live ETL must be made relationship-complete or remain report-only.

## What Changes

- Inventory every foreign-key and logical relationship affected by Work and Manifestation merges.
- Reparent or explicitly preserve all dependent records before deleting duplicates, with conflict policies for unique constraints.
- Replace the partial JSON snapshot with a complete, verified rollback artifact or require an operator-provided database backup before mutation.
- Make dry-run output show every proposed relationship change and guarantee zero database writes.
- Add transaction, rollback, idempotence, duplicate-conflict, and failure-injection tests.
- Default production execution to a safe review/confirmation mode until the complete backup and relationship checks pass.

## Capabilities

### New Capabilities

### Modified Capabilities

- `operations/frbr-etl`: Require relationship-complete, backup-verifiable, idempotent FRBR reconciliation with safe dry-run/live-mode boundaries.

## Impact

- `scripts/etl_frbr_strict.py`, FRBR/social/inventory models, migrations if needed, backup tooling, Makefile operations, and ETL tests.
- Existing catalog IDs may be reparented by explicit migration policy; no silent cascade deletion is acceptable.
