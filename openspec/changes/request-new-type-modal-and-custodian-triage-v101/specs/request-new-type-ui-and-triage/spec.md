## Purpose
Provide the collector-facing `<RequestNewTypeModal />` in the Scanner and Feedback views and render `new_media_type` proposals in the Custodian triage queue.

## ADDED Requirements

### Requirement: Collector New Media Type Request Modal & Custodian Triage Rendering

The Scanner manual-entry fallback (`/scan`) and `/feedback` page SHALL provide a `<RequestNewTypeModal />` allowing users to submit a `new_media_type` proposal, and `escalation-queue.tsx` (`/admin/content`) SHALL render `new_media_type` requests with their proposed category, format, FRBR class, and sample identifier so custodians can approve or reject them.

#### Scenario: Collector opens Request New Media Type modal from Scanner fallback
- **GIVEN** a barcode scan on `/scan` returns no match because the media format is unsupported
- **WHEN** the user clicks `"Request new media type"` in the manual entry fallback
- **THEN** `<RequestNewTypeModal />` opens with `sample_identifier_or_url` pre-filled with the scanned barcode, and submitting it adds the proposal to the Custodian User Requests queue.
