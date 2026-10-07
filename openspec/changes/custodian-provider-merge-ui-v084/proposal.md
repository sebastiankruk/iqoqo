## Why

Dev-note requirement (#ux #custodian #v083, scheduled to v0.8.4): "we could have an UI for custodian to select which pieces of data from different providers to choose for the final FRBR description; this is separate from having a smart way of just filling in the blanks on main fields like cover or even author by merging different sources". Release planning: v0.8.x, C63 (target v0.8.4).

Premises verified against code:
- **Confirmed: Custodian lacks per-field provider selection surface.** When multiple providers return conflicting or complementary metadata fragments (e.g. Google Books vs Open Library vs Allegro), custodians have no side-by-side inspection tool to choose attributes per tier. They must either accept the automatic merge or manually retype values in the FRBR editor.
- **Confirmed: Permission and audit infrastructure exist.** `PermissionName.WRITE_METADATA` and `EntityAuditLog` (`app/api/admin.py:45`) already exist, providing the required permission boundary and audit trail for custodian interventions.
- **Confirmed: Multi-provider provenance dependency.** Builds directly on C57 (`multi-provider-gap-fill-v084`), which captures raw provider payloads and per-field provenance.

## What Changes

- **Custodian Provider Merge Dialog:** Provide an administrative / custodian modal in `frontend/components/admin/provider-merge-dialog.tsx` displaying provider fragments side-by-side.
- **FRBR-Tier Grouped Field Selection:** Group selectable fields cleanly into FRBR tiers:
  - *Work (F1):* Title, Authors, Genres, Description.
  - *Expression (F2):* Language, Content Type.
  - *Manifestation (F3):* Publisher, Publication Date, ISBN-13, Cover Art.
- **Atomic Selective Merge API:** Expose `POST /api/v1/admin/frbr/manifestation/<id>/provider-merge` allowing custodians to submit a field-to-provider selection map. The backend updates the FRBR entity hierarchy in a single atomic transaction and logs the intervention to `EntityAuditLog`.

## Capabilities

### New Capabilities

- `custodian-provider-merge`: Provides an interactive curation interface for custodians to compare metadata fragments across external providers side-by-side and select individual winning attributes per FRBR tier.

### Modified Capabilities

None.

## Impact

- **Frontend:** `frontend/components/admin/provider-merge-dialog.tsx`, FRBR editor action menu integration.
- **Backend:** `app/api/admin.py`, `app/core/frbr_service.py`.
- **Tests:** Pytest verifying atomic update of chosen fields and audit log recording; Vitest component tests testing custodian attribute selection and submission.
