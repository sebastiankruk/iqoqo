---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Permissions & Configuration

- [x] 1.1 Add `escalate:request` and `escalate:resolve` permission entries to `shared/permissions.yaml`
- [x] 1.2 Run `scripts/sync_permissions.py` to regenerate `frontend/lib/permissions.ts` and seed DB permissions
- [x] 1.3 Add `escalate:request` to default role permissions and `escalate:resolve` to admin/custodian role permissions

## 2. Database Model & Migration

- [x] 2.1 Add `EscalationRequest` model to `app/db/models.py` with polymorphic FRBR-level foreign keys (`work_id`, `expression_id`, `manifestation_id`, `item_id`), `user_id`, `field_name`, `current_value`, `suggested_value`, `note`, `status` (default `pending`), `resolved_by`, `resolved_at`, `resolution_note`, `created_at`, `updated_at`
- [x] 2.2 Add `CHECK` constraint ensuring exactly one FRBR-level FK is non-NULL
- [x] 2.3 Add cascade-delete FKs on the FRBR entity columns (matching `SocialFeedback` pattern)
- [x] 2.4 Generate Alembic migration: `alembic revision --autogenerate -m "add escalation_requests table"`
- [x] 2.5 Run `alembic upgrade head` and verify table creation

## 3. Backend API Endpoints

- [x] 3.1 Add `_validate_escalation_input()` helper in `app/api/social.py` — validate `field_name` (required string, sanitized), `suggested_value` (required string ≤ 2048 chars, sanitized), `current_value` (optional string, sanitized), `note` (optional string ≤ 2048 chars, sanitized)
- [x] 3.2 Add `POST /api/escalations/<level>/<target_id>` endpoint — `@require_auth` + `@require_permission(PermissionName.ESCALATE_REQUEST)`, calls `_verify_target_exists`, creates `EscalationRequest` with status `pending`, returns 201
- [x] 3.3 Add `GET /api/escalations/mine` endpoint — `@require_auth`, returns all escalation requests by the current user ordered by `created_at` desc
- [x] 3.4 Add `GET /api/escalations/queue` endpoint — `@require_auth` + `@require_permission(PermissionName.ESCALATE_RESOLVE)`, returns all `pending` requests ordered by `created_at` asc, includes requester display name via joined load
- [x] 3.5 Add `PATCH /api/escalations/<int:escalation_id>` endpoint — `@require_auth` + `@require_permission(PermissionName.ESCALATE_RESOLVE)`, validates status transition (`pending` → `accepted` | `rejected` | `duplicate`), sets `resolved_by`, `resolved_at`, optional `resolution_note`
- [x] 3.6 Add `to_dict()` method on `EscalationRequest` model, including requester username and FRBR target info

## 4. Backend Tests

- [x] 4.1 Write `tests/test_api_escalations.py` — test escalation creation (valid, missing fields, invalid level, non-existent target, oversized text, HTML stripping)
- [x] 4.2 Test `GET /api/escalations/mine` — authenticated returns own requests, unauthenticated returns 401
- [x] 4.3 Test `GET /api/escalations/queue` — custodian sees all pending, regular user gets 403
- [x] 4.4 Test `PATCH /api/escalations/<id>` — custodian can accept/reject/mark-duplicate, regular user gets 403, invalid status returns 400
- [x] 4.5 Test cascade delete — delete target Manifestation, verify associated escalation is removed

## 5. Frontend API Client & Types

- [x] 5.1 Add `EscalationRequest` TypeScript interface to `frontend/types/frbr.ts`
- [x] 5.2 Add API client functions in `frontend/lib/api/escalations.ts`: `createEscalation()`, `getMyEscalations()`, `getEscalationQueue()`, `resolveEscalation()`
- [x] 5.3 Add React Query hooks: `useCreateEscalation()`, `useMyEscalations()`, `useEscalationQueue()`, `useResolveEscalation()` in `frontend/lib/api/escalations.ts`

## 6. Frontend Escalation Trigger Component

- [x] 6.1 Create `frontend/components/escalation/escalation-trigger.tsx` — a Shadcn `Dialog`-based component with a trigger button (Lucide `HelpCircle` icon + "Ask custodians for help" label), form fields for `field_name` (select from common fields: title, isbn, format, author, year), `suggested_value` (text input), and optional `note` (textarea)
- [x] 6.2 Wire the component to the `useCreateEscalation()` hook, show `toast.success` on submission and `toast.error` on failure
- [x] 6.3 Add i18n translation keys in relevant locale files for trigger label, dialog title, field labels, success/error messages
- [x] 6.4 Wire the component to `useMyEscalations()` to filter for escalations on the current `targetId`. If an escalation exists, conditionally render its status (`pending`, `accepted`, `rejected`) and any `resolution_note` instead of the default "Ask custodians for help" button.

## 7. Integration into Item & Manifestation Views

- [x] 7.1 Mount `<EscalationTrigger>` in `frontend/components/item/item-actions.tsx` — render above or alongside the "Admin Actions" panel, visible when `!hasPermission(PermissionName.WRITE_METADATA)` and user is authenticated, pass `level="item"` and `targetId={item.id}`
- [x] 7.2 Mount `<EscalationTrigger>` in `frontend/components/manifestation/manifestation-actions.tsx` — same inverse-permission gating, pass `level="manifestation"` and `targetId={manifestation.id}`
- [x] 7.3 Verify escalation trigger does NOT appear for custodian/admin users who have `write:metadata`

## 8. Frontend Tests

- [x] 8.1 Write Vitest + RTL test for `<EscalationTrigger>` — renders when user lacks `write:metadata`, hidden when user has it, form submission calls API
- [x] 8.2 Write Vitest + RTL test for `<EscalationTrigger>` — renders existing escalation status and resolution note when active escalation data is provided
- [x] 8.3 Write Vitest test for `item-actions.tsx` integration — verify escalation trigger renders for member role, hidden for admin role
- [x] 8.4 Write Vitest test for `manifestation-actions.tsx` integration — same visibility assertions

## 9. Lint, Format & QA

- [x] 9.1 Run `make format-python` and `make format-js`
- [x] 9.2 Run `make lint` — ensure zero warnings/errors
- [x] 9.3 Run `make test` — ensure all existing + new tests pass
