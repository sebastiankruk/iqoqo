## Context

In v0.8.3, C45 (`item-ownership-reassignment-v083`) introduced atomic physical item ownership reassignment, restricted exclusively to users with the `admin` role via `@admin_required` in `app/api/admin.py` and guarded by `isAdmin` in `frontend/app/admin/ownership/page.tsx`. However, in day-to-day community library operations, custodians actively triage and reconcile inventory across member accounts. Restricting this tool strictly to server administrators creates an operational bottleneck. See `proposal.md` for motivation.

## Goals / Non-Goals

**Goals:**
- Extend authorization for item ownership preview and reassignment endpoints to allow users with either the `admin` role or `custodian` role (holding `write:users` permission).
- Expose an "Item Ownership" navigation item in `frontend/components/admin/admin-sidebar.tsx` under the "Custodians" section.
- Update `frontend/app/admin/ownership/page.tsx` access guards to admit custodians.
- Preserve immutable `ItemCustodyEvent` provenance logs attributing transfers to the acting custodian.

**Non-Goals:**
- Self-service reassignment by ordinary members or borrowers (ownership changes remain privileged).
- Reassigning virtual Wishlist items or modifying FRBR Work/Expression/Manifestation metadata.

## Decisions

### Decision 1: Shared endpoint authorization decorator
- **Approach:** Introduce `@admin_or_custodian_required` decorator in `app/api/decorators.py` (or check `user.roles` for `admin` or `custodian`) on `/ownership/accounts`, `/ownership/source-items`, `/ownership/preview`, and `/ownership/reassign`.
- **Rationale:** Keeps authorization declarative and DRY, matching existing `@admin_required` conventions while ensuring non-privileged accounts cannot trigger ownership mutations.
- **Alternatives Considered:** Creating separate `/custodian/ownership/*` endpoints. Rejected because business logic and atomic transactions in `app/services/item_reassignment.py` are identical and duplicating routes introduces drift.

### Decision 2: AdminSidebar Custodian Section Placement
- **Approach:** Add the "Item Ownership" navigation link inside `frontend/components/admin/admin-sidebar.tsx` under the `Custodians` section, conditioned on `canWriteUsers && (roles.includes("admin") || roles.includes("custodian"))`.
- **Rationale:** Directly aligns with user requirement ("should be available from custodians part of menu - together with other custodians items"). Custodians already use `/admin/content`, `/admin/duplicates`, and `/admin/lod`.

### Decision 3: Audit Trail Attribution
- **Approach:** Retain existing `ItemCustodyEvent` schema which logs `actor_id` as the acting `user.id`.
- **Rationale:** Zero schema migration required; fully captures custodian accountability.

## Risks / Trade-offs

- **[Risk]** Custodian reassigning items belonging to other users without authorization.
  → *Mitigation:* Require `write:users` permission in addition to role, and enforce mandatory preview confirmation with deterministic SHA-256 fingerprinting.
