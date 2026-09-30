## Why

The 0.7.12 release introduced a powerful new curation loop (User Requests/Escalation Queue) and analytics features. However, extensive team reviews identified critical security risks (unprotected mutation endpoints), database cascade deletion hazards, race conditions, performance bottlenecks (unbounded SQL queries), and UX bloat (action button density). We need to resolve these issues to make the v0.7.12 release stable, secure, and user-friendly before merging to main.

## What Changes

- **Security**: Add missing `@require_permission` decorators to all FRBR mutation endpoints (`update_work`, `update_expression`, `update_manifestation`, `update_item`) and cover upload routes.
- **Data Integrity**: Fix Alembic migration `20260722_add_escalation_requests_table` to include missing `target_type` and `request_type` columns.
- **Data Integrity (BREAKING)**: Implement explicit safeguards in deletion request resolution to block deleting a `Manifestation` if dependent `Item` records exist, preventing cascading physical inventory destruction.
- **Security**: Prevent IDOR on Item deletion requests by verifying resolver/requester ownership over the physical item.
- **Resilience**: Enforce explicit atomic transaction blocks (`with_for_update`, `synchronize_session=False`) during escalation resolution to prevent race conditions.
- **Performance**: Enforce a 12-month bounding window on `get_velocity_stats()` to allow index pruning and prevent unbounded PostgreSQL scans.
- **UX**: Consolidate `useEffect` hooks in `scanner/page.tsx` for cleaner `localStorage` state management.
- **UX**: Refactor the item and manifestation action layouts to render all admin actions (Refetch Cover, Regenerate Cover, Edit Cover Art, Remove / Delete) as direct inline buttons. Overflow `<DropdownMenu>` was trialled and reverted as a confusing anti-pattern.
- **UX**: De-clutter `EscalationQueue` request cards by rendering Accept, Reject, and Mark as Duplicate as direct inline buttons per card — overflow menus were reverted per UX feedback.
- **UX**: Move policy selector on the scanner UI into a floating pill to save vertical viewport space.

## Capabilities

### New Capabilities

- `finalize-0-7-12-hardening`: General security, data integrity, and analytics bounding fixes for the 0.7.12 release.

### Modified Capabilities

- `deletion-request-resolution`: Adding cascade safeguards, IDOR prevention, and atomic transactions.
- `escalation-queue-ui`: Streamlining the UI density and reducing action buttons per card.
- `user-requests-manifestation-layout`: Consolidating action panels to prevent UI bloat.
- `scanner-persistence`: Cleaning up local storage synchronization.

## Impact

- **API/Security**: `/frbr/*` mutation routes will now properly enforce permissions, returning 403 where applicable.
- **Database**: Modified Alembic migrations will prevent 500 errors on the escalation table. New data integrity checks will block certain deletion operations if cascading is detected.
- **Frontend UI**: Action layouts on entity pages and the admin escalation queue expose all actions as direct inline buttons — dropdown menus were evaluated and reverted as a UX anti-pattern. Scanner UI will have more vertical breathing room.
