## Why
With the backend `new_media_type` escalation endpoint ready in `C107`, collectors need a frictionless UI trigger right where they discover a missing format (inside the Scanner manual-entry fallback, the media type selector, and `/feedback` / `/help`), and Custodians need a clean triage card in `/admin/content` (`escalation-queue.tsx`).

## What Changes

- **`<RequestNewTypeModal />` Component (`frontend/components/social/request-new-type-modal.tsx`):** Build a Shadcn Dialog form allowing collectors to propose a new Media Category or Physical Format (`proposed_category`, `proposed_format`, `parent_frbr_class`, `sample_identifier_or_url`, `rationale`), pre-filling any barcode/query already entered on `/scan`.
- **Entry Points in Scanner & Feedback:** Mount `"Can't find your media format? Request a new type"` link in the `/scan` manual-entry fallback and `/feedback` ("My Requests") page without exceeding the $\le 4$ visible buttons limit.
- **Custodian Triage View (`frontend/components/admin/escalation-queue.tsx`):** Render `new_media_type` proposals in the Admin/Custodian User Requests queue with structured badges (`Proposed Category`, `Proposed Format`, `FRBR Class`, `Sample Barcode/URL`) and Approve / Defer / Reject resolution actions.

## Capabilities

### New Capabilities
- `request-new-type-ui-and-triage`: Frontend `<RequestNewTypeModal />` triggered from Scanner/Feedback and Custodian triage rendering in `escalation-queue.tsx`.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/components/social/request-new-type-modal.tsx`
- `frontend/app/scan/page.tsx`, `frontend/app/feedback/page.tsx`
- `frontend/components/admin/escalation-queue.tsx`
- `frontend/messages/en.json`, `frontend/messages/pl.json`
- `frontend/__tests__/components/social/request-new-type-modal.test.tsx`
