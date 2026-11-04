## Why
Administrators and collectors expressed confusion in `iqoqo development notes.md` (*"it is still unclear how does peering works - if it is not bilateral - what does it mean when I..."*) about what happens when Instance A adds/trusts Instance B unilaterally versus when both instances peer reciprocally.

## What Changes

- **Peering Directionality Status & Effective Capabilities Matrix (`federation-instances.tsx`):** Display an explicit **Peering Directionality Badge** (`Bilateral / Reciprocal`, `Outbound Only (Unilateral)`, `Inbound Only`, or `Blocked`) on each peer row in `/admin/federation`, accompanied by a concise **Effective Capabilities Popover / Matrix** explaining exactly what works in the current state:
  - **Local `trusted` (Unilateral Outbound):** Auto-fills missing FRBR metadata from their catalog (`prov:wasDerivedFrom`) and allows local users to send `@user@domain` follow requests to them.
  - **Local `untrusted` (Unilateral Outbound):** Routes incoming metadata updates from them into the Custodian `ProviderMergeDialog` review queue rather than auto-applying.
  - **Reciprocal Peering (Both sides non-blocked & reachable):** Required for two-way `@user@domain` friend connections, `friends_only` collection browsing, and cross-instance `as:Offer` / `as:Accept` item loans.
- **In-App Help Guide Expansion (`/help/federation`):** Add a clear visual diagram and table to `/help` explaining unilateral trust vs. bilateral peering.

## Capabilities

### New Capabilities
- `federation-peering-directionality-ux`: Explicit peering directionality indicators (`Reciprocal` vs `Unilateral`) and an effective capabilities matrix in `/admin/federation` and `/help`.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `app/api/admin.py` / `app/core/federation_discovery.py` (expose inbound/reciprocal activity signal on instance serialization)
- `frontend/components/admin/federation-instances.tsx`
- `frontend/app/help/[slug]/page.tsx` (or `/help` content)
- `frontend/messages/en.json`, `frontend/messages/pl.json`
