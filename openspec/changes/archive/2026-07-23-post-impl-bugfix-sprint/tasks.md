---
type: Concept
title: tasks
timestamp: 2026-07-23T00:48:00Z
---

## 1. Permission Role Assignment (Bug #1 + #4)

- [x] 1.1 Create Alembic data migration: `alembic revision -m "assign escalation permissions to roles"` — INSERT `escalate:request` permission into `role_permissions` for the `user` role, INSERT `escalate:resolve` into `role_permissions` for `custodian` and `admin` roles. Use a SELECT to find the permission and role IDs. Use `ON CONFLICT DO NOTHING` for idempotency.
- [x] 1.2 Run `alembic upgrade head` and verify the permissions are correctly assigned by querying `role_permissions` join table.
- [x] 1.3 Verified via backend tests: `escalations_setup` fixture grants permissions, and tests confirm create/list/resolve flow works correctly.
- [x] 1.4 Diagnosed: root cause = permissions not assigned to roles in the database. The Alembic migration fixes this. Backend routes are properly decorated with `@require_permission`. Frontend hooks (`useMyEscalations`, `useEscalationQueue`) use correct API paths `/api/escalations/mine` and `/api/escalations/queue`. No contract mismatch exists. End-to-end test `test_submit_to_retrieve_pipeline` validates the full pipeline.

## 2. Fix "Edit FRBR" Button Visibility (Bug #3)

- [x] 2.1 In `frontend/components/item/item-actions.tsx`: changed gating from `READ_METADATA` to `WRITE_METADATA`.
- [x] 2.2 In `frontend/components/manifestation/manifestation-actions.tsx`: changed gating from `READ_METADATA` to `WRITE_METADATA`.
- [x] 2.3 Updated `showAdminActions` in both components: replaced `READ_METADATA` with `WRITE_METADATA`.
- [x] 2.4 Verified via frontend tests: "Edit FRBR" NOT visible with `read:metadata` alone; visible with `write:metadata`.

## 3. Fix FRBR Search Access for Custodians (Bug #5)

- [x] 3.1 In `app/api/admin.py`: replaced `@admin_required` with `@require_permission(PermissionName.READ_METADATA)`. Imported `require_permission`.
- [x] 3.2 Removed the redundant `_has_permission(user, PermissionName.READ_METADATA)` check.
- [x] 3.3 Removed the `user = _get_current_user()` call from `search_frbr_entities()`.
- [x] 3.4 Verified via backend test: custodian with `read:metadata` gets 200; plain user gets 403.

## 4. Build Escalation Queue Admin UI (Bug #2)

- [x] 4.1 Created `frontend/components/admin/escalation-queue.tsx` with card-based list showing requester name, target level+ID, field name, suggested value, note, timestamp.
- [x] 4.2 Added Accept/Reject/Duplicate buttons with inline resolution note form, calling `useResolveEscalation()`.
- [x] 4.3 Added empty state and loading skeleton (pulse animation).
- [x] 4.4 Mounted as "Escalation Queue" tab in `frontend/app/admin/content/page.tsx`, gated on `escalate:resolve`.
- [x] 4.5 No i18n system used for admin labels — skipped.
- [x] 4.6 Verified via frontend integration test: tab renders for custodian, hidden for regular user.

## 5. Fix PIL Fallback Cover Visual Regression (Bug #6)

- [x] 5.1 Removed CTA text rendering block.
- [x] 5.2 Increased footer font to 28px, switched to DejaVuSans-Bold.ttf.
- [x] 5.3 Centered footer text using `textbbox()`.
- [x] 5.4 Added 1px #475569 horizontal line above footer, spanning 60% width.
- [x] 5.5 Moved author_y from `height - 190` to `height - 150`.
- [x] 5.6 Verified: all 23 cover tests pass, confirming valid JPEG output.

## 6. Backend Tests

- [x] 6.1 Added `test_submit_to_retrieve_pipeline` — end-to-end submit-to-retrieve via /mine and /queue.
- [x] 6.2 Added `test_custodian_can_view_queue` — custodian gets 200 on queue endpoint.
- [x] 6.3 Added `test_frbr_search_by_custodian_with_read_metadata` — non-admin with read:metadata gets 200.
- [x] 6.4 Added `test_frbr_search_by_plain_user_without_read_metadata` — user without read:metadata gets 403.
- [x] 6.5 No assertion changes needed for cover tests — they validate format/dimensions, not specific text.

## 7. Frontend Tests

- [x] 7.1 Updated `item-actions.test.tsx`: "Edit FRBR" NOT visible with `read:metadata`; visible with `write:metadata`.
- [x] 7.2 Updated `manifestation-actions.test.tsx`: same visibility assertions.
- [x] 7.3 Created `escalation-queue.test.tsx`: loading state, empty state, pending requests rendering, resolve buttons, various FRBR target levels.
- [x] 7.4 Created `admin-content-escalation.test.tsx`: Escalation Queue tab visible for custodian, hidden for regular user.

## 8. Lint, Format & QA

- [x] 8.1 Ran `make format-python` and `make format-js` — all files formatted.
- [x] 8.2 ESLint on changed files — zero errors/warnings. Ruff on changed Python files — all checks passed.
- [x] 8.3 All tests pass: 37/37 backend tests, 97/97 frontend tests (across 15 test files).
