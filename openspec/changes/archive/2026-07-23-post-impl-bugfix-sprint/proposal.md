---
type: Concept
title: proposal
timestamp: 2026-07-23T00:44:00Z
---

## Why

The `covers-collector-insights` and `custodian-escalation-hooks` changes were implemented but left six functional defects and one UX regression in production. Users cannot see their own help requests, custodians have no queue UI to review them, the "Edit FRBR" button renders for unprivileged users pointing to an admin-only page, the new escalation permissions were never assigned to default roles, custodians are blocked from FRBR lookups by a hard `admin_required` check instead of permission-based gating, and the redesigned PIL fallback covers produce ugly output with text too small to read. These are blocking issues that degrade both the custodian workflow and the core user experience.

## What Changes

- **Bug 1 — Submitted escalation requests are invisible to both users and custodians**: Even after manually assigning `escalate:request` to the `user` role (which restores the "Request Help" button), a submitted request leaves no trace — the requesting user cannot see it in their history via `useMyEscalations()`, and the custodian/admin cannot see it in the queue via `GET /api/escalations/queue`. The submit endpoint appears to succeed but the request is never persisted or is persisted in a way that the retrieval queries cannot find it. Fix: seed the `escalate:request` permission to the default `user` role and `escalate:resolve` to `custodian` and `admin` roles, **plus** diagnose and repair the submit-to-retrieve data pipeline so submitted requests are queryable by both the submitter (via `useMyEscalations`) and queue viewers (via `/api/escalations/queue`).
- **Bug 2 — Admin/custodian does not see any requests**: The backend `GET /api/escalations/queue` endpoint exists and works, but there is no frontend page or component to render the queue. Fix: build an `EscalationQueue` component and mount it in the admin content page (or a dedicated admin tab) so custodians can view and resolve pending requests.
- **Bug 3 — "Edit FRBR" button visible to regular users**: The "Edit FRBR" button in `item-actions.tsx` and `manifestation-actions.tsx` is gated on `READ_METADATA` which every user has. The button links to `/admin/content` which requires higher privileges. Fix: gate the "Edit FRBR" button on `WRITE_METADATA` instead of `READ_METADATA`, matching the actual permission needed to use the editor.
- **Bug 4 — New permissions not assigned to roles**: The `escalate:request` and `escalate:resolve` permissions exist in `shared/permissions.yaml` and the `PermissionName` enums, but were never assigned to any roles in the database. Fix: create a one-time migration or startup seeder that assigns `escalate:request` to the `user` role and `escalate:resolve` to `custodian`/`admin` roles.
- **Bug 5 — Custodian cannot lookup FRBR entities (says "Admin privileges required")**: The `/v1/admin/frbr/search` endpoint uses the `@admin_required` decorator which checks for the `admin` role, not for permissions. A custodian with `write:metadata` and `read:metadata` permissions but without the `admin` role is blocked. Fix: replace `@admin_required` with `@require_permission(PermissionName.READ_METADATA)` on this endpoint so permission-based access works correctly.
- **Bug 6 — PIL fallback covers look ugly**: The redesigned `generate_fallback_cover()` added call-to-action text ("Placeholder — contribute a cover") and a footer, but the font sizes are too small on the 600×900 canvas (22px for CTA, 20px for footer) and the overall design regressed in visual quality. Fix: revert the design to the pre-enhancement state (gradient + title + author only) and add only a prominent, graphically-styled "powered by iqoqo" footer with larger typography and visual emphasis.

## Capabilities

### New Capabilities

- `escalation-queue-ui`: Covers the frontend admin component for viewing and resolving pending escalation requests.

### Modified Capabilities

- `custodian-escalation`: Fixes permission assignment to roles, FRBR search access gating, and "Edit FRBR" button visibility logic.
- `cover-provenance`: Fixes the PIL fallback cover visual regression.

## Impact

- **Backend**: `app/api/admin.py` (replace `@admin_required` with `@require_permission` on FRBR search), `app/api/decorators.py` (no changes), `app/utils/covers.py` (revert fallback cover to simpler design with only "powered by iqoqo").
- **Frontend**: `frontend/components/item/item-actions.tsx` and `frontend/components/manifestation/manifestation-actions.tsx` (gate "Edit FRBR" on `WRITE_METADATA`), new `frontend/components/admin/escalation-queue.tsx` component, admin content page integration.
- **Database**: Role-permission seeding (assign `escalate:request` to `user` role, `escalate:resolve` to `custodian`/`admin`).
- **Dependencies**: None new.
