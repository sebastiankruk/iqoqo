## Why

Currently, Item Ownership Reassignment is strictly restricted to system administrators with the `admin` role at `/admin/ownership`. However, library custodians routinely manage inventory corrections, physical batch ingest reconciliation, and catalog attribution across member accounts. Restricting ownership reassignment exclusively to system administrators forces routine catalog curation tasks to be escalated to instance administrators, creating unnecessary administrative bottlenecks. Addressing this in `v0.8.4` directly fulfills dev-note item `#v084` ("“Item Ownership Reassignment” should be available for custodians - not only for admins - and should be available from custodians part of menu - together with other custodians items #ux #v084").

## What Changes

- **Custodian Role Authorization:** Update ownership reassignment backend endpoints (`preview_reassignment` and `execute_reassignment`) to permit users with either the `custodian` role or `admin` role.
- **Custodian Navigation Menu Exposure:** Expose a dedicated entry point for Item Ownership Reassignment within the custodian dropdown and dashboard menu alongside existing custodian tools (duplicates review, merge comparison, etc.).
- **Route Access & Guardianship:** Allow custodians to access the ownership management view (`/admin/ownership` or an aliased `/custodian/ownership` route) without 403 authorization rejections.
- **Audit Logging Attribution:** Ensure custody transfer events record the acting user ID regardless of whether they are an administrator or a custodian.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `item-ownership-reassignment`: Extend ownership reassignment authorization policy to permit users with the `custodian` role, and expose the feature within the custodian navigation surface.

## Impact

- **Backend:** `app/api/admin.py` or `app/services/item_reassignment.py` authorization decorators (`@require_role` / permission checks).
- **Frontend:** Navigation components (`frontend/components/layout/nav-user.tsx` / `frontend/components/layout/custodian-menu.tsx` or similar), routing middleware / guards.
- **Specs:** Delta spec updating `openspec/specs/item-ownership-reassignment/spec.md`.
- **Tests:** Backend tests in `tests/test_item_reassignment.py` (verify custodian role can preview and reassign) and frontend component tests verifying menu visibility for custodians.
