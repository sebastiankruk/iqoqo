## 1. Database and Schema

- [x] 1.1 Fix Alembic migration `20260722_add_escalation_requests_table.py` by adding missing `target_type` and `request_type` columns.

## 2. API Security and Resilience

- [x] 2.1 Add `@require_permission(PermissionName.WRITE_METADATA)` (or appropriate permissions) to `/frbr/*` mutation routes and `/media/upload-cover` in `app/api/admin.py`.
- [x] 2.2 Update `resolve_escalation_request` in `app/api/social.py` to verify ownership of physical items before allowing deletion requests for them to proceed.
- [x] 2.3 Refactor `resolve_escalation_request` to wrap operations in atomic transactions (`with_for_update()`, `synchronize_session=False`), and add a check blocking manifestation deletion if dependent items exist.
- [x] 2.4 Add a 12-month bounding window to `get_velocity_stats` in `app/core/data_manager.py`.

## 3. Frontend UX Refactoring

- [x] 3.1 Consolidate duplicate `useEffect` hooks in `frontend/app/scan/page.tsx` for clean `localStorage` synchronization.
- [x] 3.2 Relocate the policy selector in the scanner UI to a floating pill over the bottom-right of the viewfinder.
- [x] 3.3 Refactor `EscalationQueue` in `frontend/components/admin/escalation-queue.tsx` to restrict cards to one primary CTA, pushing secondary actions (Reject, Duplicate) to an overflow DropdownMenu.
- [x] 3.4 Refactor entity action layouts (`item-actions.tsx`, `manifestation-actions.tsx`) to strictly enforce a maximum of 4 buttons per container, nesting tertiary commands in a dropdown.
- [x] 3.5 Refactor the `EscalationTrigger` to appear as an un-collapsed outline button directly in the action layout when a user has no active requests for that target.
