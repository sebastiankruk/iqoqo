---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

Normal users cannot modify locked system-level metadata on Manifestation records (titles, ISBNs, format classifications) because those fields are protected behind custodian/admin RBAC permissions. When a user spots incorrect metadata — a wrong ISBN, a misclassified format, or a missing subtitle — they have no structured way to request a correction. This creates a dead-end UX where the user sees the problem but cannot act on it. Custodian Escalation Hooks bridge this gap by giving every authenticated user a lightweight "Ask Custodians for Help" flow that safely queues metadata change requests for administrative review without granting elevated write access.

## What Changes

- **New escalation request API**: A new set of REST endpoints under `app/api/social.py` to create, list, and resolve custodian escalation requests, reusing the existing FRBR-level targeting pattern (`/escalations/<level>/<target_id>`).
- **New `EscalationRequest` database model**: A new table capturing the requesting user, target FRBR entity, requested field, suggested value, status lifecycle (pending → accepted / rejected), and optional custodian response note.
- **New frontend escalation trigger component**: A reusable `<EscalationTrigger>` component rendered on item and manifestation detail pages where the user lacks write permissions to locked fields.
- **Integration into `item-actions.tsx`**: Mount the escalation trigger inside the existing item detail actions panel, visible to authenticated users who do NOT have `write:metadata` permission.
- **Integration into `manifestation-actions.tsx`**: Mount the escalation trigger on the manifestation detail view, similarly gated for non-custodian users.
- **New `escalate:request` permission**: A new permission in `shared/permissions.yaml` controlling who can submit escalation requests (granted to the default `member` role).

## Capabilities

### New Capabilities

- `custodian-escalation`: Covers the full user-to-custodian escalation lifecycle — request submission, queue listing, status transitions (accept/reject), and integration with the existing RBAC permission model.

### Modified Capabilities

- `item-custody`: Adds requirement that custody-adjacent views (item detail, manifestation detail) expose escalation hooks for users without elevated metadata write permissions.

## Impact

- **Backend**: `app/api/social.py` (new endpoints), `app/db/models.py` (new `EscalationRequest` model), `app/api/decorators.py` (no changes — reuses existing `require_auth` + `require_permission`), `shared/permissions.yaml` + `frontend/lib/permissions.ts` (new `escalate:request` and `escalate:resolve` permissions).
- **Frontend**: `frontend/components/item/item-actions.tsx`, `frontend/components/manifestation/manifestation-actions.tsx` (embed trigger), new `frontend/components/escalation/escalation-trigger.tsx` component.
- **Database**: New Alembic migration for `escalation_requests` table with foreign keys to `users` and polymorphic FRBR-level columns (same pattern as `SocialFeedback`).
- **i18n**: New translation keys for escalation labels, toast messages, and status badges.
