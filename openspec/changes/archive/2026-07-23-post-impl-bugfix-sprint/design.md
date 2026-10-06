---
type: Concept
title: design
timestamp: 2026-07-23T00:46:00Z
---

## Context

Two openspec changes — `covers-collector-insights` and `custodian-escalation-hooks` — were implemented and merged. The backend API endpoints, database models, frontend components, and tests all exist and pass. However, six integration-level defects surfaced during manual QA:

1. The `escalate:request` and `escalate:resolve` permissions were added to `shared/permissions.yaml` and the enum files, but never assigned to any database role. No user — regardless of role — can submit or resolve escalations. Even after manually assigning the permission, submitted requests are invisible to both the submitter and the queue viewer — the submit-to-retrieve pipeline is broken beyond the permission layer.
2. The custodian queue backend endpoint (`GET /api/escalations/queue`) works, but no frontend page or component exists to render it.
3. The "Edit FRBR" button uses `READ_METADATA` permission gating, but the destination page (`/admin/content?tab=metadata`) requires higher-level access — all authenticated users see a button that leads to a page they cannot use.
4. The FRBR entity search endpoint (`/v1/admin/frbr/search`) uses `@admin_required` (hard role check for "admin") instead of a permission-based check. Custodians with `write:metadata` and `read:metadata` get a 403 "Admin privileges required" when trying to look up entities in the FRBR editor.
5. The redesigned PIL fallback cover added CTA text and a footer with font sizes too small (22px, 20px on a 600×900 canvas), producing covers that look worse than before the change.

## Goals / Non-Goals

**Goals:**

- Restore the escalation workflow end-to-end: users can submit requests, custodians can view and resolve them
- Ensure UI buttons only appear when the user can actually complete the action behind them
- Allow custodians (not just admins) to use the FRBR search / metadata editor
- Revert the PIL fallback cover to a clean design with only a prominent "powered by iqoqo" footer
- Achieve all fixes with minimal blast radius — targeted edits, no architectural changes

**Non-Goals:**

- Introducing new features beyond restoring what was designed in the original openspec changes
- Changing the RBAC model or introducing new roles
- Modifying the cover pipeline tier ordering
- Building a full notification center for escalation updates

## Decisions

### D1: Role-permission seeding via Alembic data migration

**Decision**: Create an Alembic data migration that assigns `escalate:request` to the `user` role and `escalate:resolve` to the `custodian` and `admin` roles using INSERT statements into the `role_permissions` join table.

**Rationale**: A data migration is idempotent, version-tracked, and runs automatically on `alembic upgrade head`. It avoids requiring manual SQL or a separate seeding script. The existing `sync_permissions.py` only syncs enum definitions, not role assignments.

**Alternative considered**: A runtime startup seeder in `create_app()`. Rejected because it runs on every boot and adds startup latency; data migrations run once.

**Note**: Permission seeding alone is not sufficient. With the permission manually assigned, a submitted request is invisible to both the submitter and the queue viewer. The root cause could be in the backend (insert logic, query filter), in the frontend (component gating, hook wiring, response mapping), or in the API contract (shape mismatch between what the endpoint returns and what the hook expects). A diagnostic pass across the full stack is required.

### D2: Gate "Edit FRBR" on `WRITE_METADATA` instead of `READ_METADATA`

**Decision**: Change the permission check for the "Edit FRBR" button in both `item-actions.tsx` and `manifestation-actions.tsx` from `PermissionName.READ_METADATA` to `PermissionName.WRITE_METADATA`.

**Rationale**: The "Edit FRBR" button navigates to `/admin/content?tab=metadata` which calls the FRBR editor. Editing FRBR metadata requires `write:metadata`. Showing the button to users who only have `read:metadata` creates a dead-end UX. The `showAdminActions` panel computation also needs updating to avoid relying on `READ_METADATA` for the FRBR edit visibility check.

### D3: Replace `@admin_required` with `@require_permission` on FRBR search

**Decision**: On the `/v1/admin/frbr/search` endpoint in `app/api/admin.py`, replace `@admin_required` with `@require_permission(PermissionName.READ_METADATA)`. Remove the redundant `_has_permission` check inside the handler body.

**Rationale**: The `@admin_required` decorator does a hard role check for the string `"admin"`. This blocks custodians who have the correct permissions (`read:metadata`, `write:metadata`) but whose role name is `"custodian"`, not `"admin"`. Permission-based gating is the correct pattern — it matches how every other content-management endpoint is protected.

### D4: Build an `EscalationQueue` component in admin content page

**Decision**: Create `frontend/components/admin/escalation-queue.tsx` that renders a tabular list of pending escalation requests with resolve actions (accept/reject/duplicate + resolution note). Mount it as a new tab in the admin content page, visible to users with `escalate:resolve` permission.

**Rationale**: The backend is fully functional. The only gap is the frontend UI. Adding it as a tab in the existing admin content page avoids creating new routes and leverages the existing permission-gated admin shell.

### D5: Revert PIL fallback cover to gradient + title + author + "powered by iqoqo" only

**Decision**: Remove the CTA text ("Placeholder — contribute a cover") and increase the "powered by iqoqo" footer font size to 28-30px with a more prominent, graphical treatment (e.g., centered at bottom with a subtle horizontal rule above it). Keep the gradient + title + author rendering as-is since those look correct.

**Rationale**: The user reported the new covers "simply look ugly" with text "way smaller than before." The CTA text adds visual noise without actionable value (users can't upload covers from the cover image itself). Keeping only "powered by iqoqo" as a footer restores visual clarity while preserving the branding intent.

## Risks / Trade-offs

- **[Data migration on running instance]** → Mitigation: The migration only INSERTs into `role_permissions`. It does not ALTER any schema. If permissions already exist (from manual fixes), the INSERT can use ON CONFLICT DO NOTHING to be safe.
- **[FRBR search now accessible to custodians]** → Trade-off accepted: This is the intended behavior per the original design. The search is read-only and already filtered to authorized data.
- **[Submit-to-retrieve gap — root cause TBD]** → Mitigation: The disconnect could be in the backend, frontend, or API contract. Diagnostic time is budgeted. The fix scope will be narrow once the root cause is identified.
- **[Existing covers not updated]** → Trade-off accepted: Only new fallback covers will use the revised design. Existing covers can be regenerated manually if desired.

## Open Questions

None — all decisions are derived directly from the bug reports and original design intent.
