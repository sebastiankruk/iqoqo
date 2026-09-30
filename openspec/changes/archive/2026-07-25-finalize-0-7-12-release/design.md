## Context

The 0.7.12 release introduced powerful user escalation pipelines and telemetry/analytics features. Review by the security, QA, SRE, and UX teams revealed unhandled edge cases including unprotected backend mutations, potential database deletion cascades, UI state redundancy, and visual bloat. This design addresses how to implement fixes for these areas seamlessly.

## Goals / Non-Goals

**Goals:**

- Implement declarative RBAC via `@require_permission` decorators on all `/frbr/*` mutation routes.
- Prevent cascading physical inventory deletions by blocking manifestation removal if bound items exist.
- Prevent IDOR by verifying physical item ownership before allowing deletion requests to proceed.
- Eliminate race conditions in escalation handling by using explicit PostgreSQL row-locking `with_for_update()`.
- Constrain analytics queries to 12 months to utilize database indexes correctly.
- Fix UI bloat by consolidating persistence hooks. All admin actions rendered as direct inline buttons — overflow dropdowns were rejected as a bad UX pattern.

**Non-Goals:**

- Creating new analytics charts (only bounding existing ones).
- Adding new RBAC roles (only applying existing ones).

## Decisions

- **Declarative RBAC:** We will explicitly add `@require_permission(PermissionName.WRITE_METADATA)` to `app/api/admin.py` mutation routes rather than relying on inner function logic, enforcing a fail-fast approach to forbidden mutations.
- **Atomic Deletions:** We will enforce `try...except` blocks with `db.session.rollback()` and disable session synchronization via `synchronize_session=False` in `app/api/social.py` to prevent partial metadata deletion.
- **Cascade Safe-guards:** Before calling `db.session.delete(target_manif)`, we will issue a fast `COUNT` check on the `items` table to block deletion and demand a disambiguation/merge workflow instead if users hold physical copies.
- **Frontend Persistence Consolidation:** In `frontend/app/scan/page.tsx`, we will load initial storage values during `useState()` initialization (using `typeof window !== "undefined"` checks) and apply EXACTLY ONE `useEffect` per state variable for persistence, eliminating DOM jitter.
- **All-Actions Inline:** All admin actions (Refetch Cover, Regenerate Cover, Edit Cover Art, Remove from library / Delete manifestation) are rendered as direct `<Button variant="outline" size="sm">` elements. For the escalation queue, Accept, Reject, and Mark as Duplicate are all rendered as direct inline buttons. Overflow `<DropdownMenu>` was reverted — hiding actions behind a `[...]` button was found to be confusing and a poor UX pattern.
- **Floating Policy Pill:** The policy selector in the scanner will be moved to a floating `backdrop-blur-md` widget over the camera view, eliminating double-stacked TopBar pills.

## Risks / Trade-offs

- [Risk] Custodians may become confused if a Manifestation deletion request is rejected due to physical items being attached. -> Mitigation: Add a clear UI error message stating "Cannot delete: Users have physical items in their inventory referencing this manifestation."
- [Risk] Bounding analytics to 12 months hides historic data. -> Mitigation: The user dashboard is primarily focused on recent acquisition momentum. 12 months is sufficient for a "Velocity Chart".
