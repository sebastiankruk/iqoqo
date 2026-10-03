## Context

The existing ETL chooses canonical Works/Manifestations and directly deletes duplicates after moving only Expressions or Items. SQLAlchemy/database cascades can remove related catalog, inventory, social, and provenance records. The current JSON snapshot covers only four core entity tables and is not a complete rollback boundary.

## Goals / Non-Goals

**Goals:**

- Make duplicate reconciliation relationship-complete and recoverable.
- Keep dry-run deterministic and write-free.
- Preserve idempotence and explicit operator control.

**Non-Goals:**

- Changing duplicate matching heuristics beyond what is needed for safe merges.
- Automatically resolving ambiguous metadata/relationship conflicts.
- Replacing the platform’s normal database backup system; the ETL must integrate with it or refuse to run.

## Decisions

1. **Build an explicit dependency inventory.** Enumerate ORM relationships and direct FK tables for Work and Manifestation before implementing merge operations. The inventory becomes a test matrix.
2. **Use reparent-then-delete with conflict checks.** For each relationship, move rows to the canonical entity when safe; for unique conflicts, retain/merge deterministically or abort the merge with no deletion.
3. **Require complete recovery coverage.** Prefer a verified database backup/restore point. If a portable artifact is retained, it must include every affected table, relationship, and pre-image required for rollback—not only core FRBR rows.
4. **Separate planning from mutation.** Dry-run produces a merge plan; live mode validates backup coverage, acquires the needed transaction/locks, applies the plan, verifies integrity, and commits atomically.
5. **Default ambiguous operations to abort.** Silent cascade behavior is never an acceptable fallback for release ETL.

## Risks / Trade-offs

- [Risk] Full relationship snapshots are large → stream/compress them or use the database backup service, but verify restore coverage before mutation.
- [Risk] Merge conflicts reduce automatic cleanup → report actionable conflict IDs for manual resolution.
- [Risk] Long transactions can block writes → process planned batches only when the recovery and locking strategy preserves atomicity.

## Migration Plan

Keep the existing command in report/dry-run mode until relationship coverage and restore tests pass. Enable live mode only after an operator-approved backup. Existing partially completed runs must be audited before rerunning; the new code must detect already-reparented records idempotently.
