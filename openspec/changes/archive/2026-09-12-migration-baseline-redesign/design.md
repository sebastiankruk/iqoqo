## Context

See `proposal.md` for motivation. Currently, the consolidated baseline was stamped with `v0_7_18_baseline`. Because release 0.7.18 introduces genuine DDL changes (`auth.token_blocklist.expires_at`, moving `instance_settings` to `config` schema, and domain CheckConstraints), stamping legacy production directly as `v0_7_18_baseline` caused Alembic to skip DDL execution, leading to schema drift and 500 crashes on authentication.

## Goals / Non-Goals

**Goals:**
- Provide a clean, two-stage linear Alembic DAG: `v0_7_17_baseline` -> `v0_7_18_fixes`.
- Ensure legacy production databases at `f65648a6aaf4` bridge safely to `v0_7_17_baseline` and naturally upgrade to `v0_7_18_fixes` via standard `flask db upgrade`.
- Ensure fresh databases boot cleanly through both migrations.
- Remove ad-hoc DDL patches from `scripts/clone.sh` and `scripts/fix_alembic.py`.
- Enforce strict revision length limits (both identifiers <= 16 chars, well below the PostgreSQL 32-character limit).

**Non-Goals:**
- Modifying FRBR ontology models or changing business logic outside of 0.7.18 review fixes.
- Restoring the 55 legacy migration files; historical squashing remains intact up to 0.7.17.

## Decisions

### Decision 1: Two-Stage Linear Migration Chain
- Anchor the consolidated baseline at `v0_7_17_baseline.py` (`down_revision = None`), matching the exact canonical state of v0.7.17 (`f65648a6aaf4`):
  - `instance_settings` in `catalog` schema.
  - `auth.token_blocklist` without `expires_at`.
  - `user_collections.parent_id` without `ondelete="SET NULL"`.
- Implement `v0_7_18_fixes.py` (`down_revision = "v0_7_17_baseline"`):
  - Creates `config` schema and moves `catalog.instance_settings` to `config`.
  - Adds `expires_at` and `ix_auth_token_blocklist_expires_at` to `auth.token_blocklist`.
  - Adds domain `CheckConstraint`s on `Item`, `UserWorkIntent`, `User`, and `LoanRequest`.
  - Updates `UserCollection.parent_id` foreign key.

*Alternatives considered:*
- *Direct squash to 0.7.18 with manual clone script fixes*: Rejected because it breaks real production upgrades where `clone.sh` is not invoked.
- *Keeping 55 individual migrations*: Rejected because the DAG had multiple heads and historical technical debt.

### Decision 2: Bridge Stamping Strategy
- In `migrations/env.py`, when a legacy revision (`f65648a6aaf4`) is detected, update `alembic_version` to `v0_7_17_baseline`.
- Because `v0_7_17_baseline` is not the DAG head, Alembic's subsequent `context.run_migrations()` automatically advances to `v0_7_18_fixes`.

### Decision 3: Idempotent DDL in v0_7_18_fixes
- In `v0_7_18_fixes.py`, use dialect-aware, idempotent operations (`ADD COLUMN IF NOT EXISTS`, `CREATE SCHEMA IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) so that any environment with partial changes applies cleanly without crashing.

## Risks / Trade-offs

- [Risk: Upgrading an environment where partial manual SQL fixes were already run] → Mitigation: Use idempotent DDL (`IF NOT EXISTS` / inspection checks) in `v0_7_18_fixes.py`.
- [Risk: Downgrade from 0.7.18 to 0.7.17 drops data in new columns] → Mitigation: Standard Alembic downgrade behavior cleanly reverses 0.7.18 changes while leaving 0.7.17 baseline intact.
