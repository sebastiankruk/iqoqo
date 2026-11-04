## Context

Collectors most often realize a media format is missing while standing at their shelf on `/scan` (or browsing `/feedback`). Providing a 1-click modal that captures the barcode they just scanned alongside their proposed format name turns a dead-end into a structured ontology contribution.

## Goals / Non-Goals

**Goals:**
- Deliver `<RequestNewTypeModal />` with pre-filled barcode/identifier support from `/scan`.
- Display `new_media_type` requests clearly in the user's `/feedback` ("My Requests") tab and the Custodian `/admin/content` (`escalation-queue.tsx`) view, where `manifestation_id` is `null`.

**Non-Goals:**
- Auto-editing `shared/format_mappings.yaml` from the browser without git/ontology validation.

## Decisions

### Handling Null `manifestation_id` in `escalation-queue.tsx`
* **Decision:** In `escalation-queue.tsx`, when `request.request_type === "new_media_type"`, render a dedicated `"New Media Type Proposal"` header badge with the proposed category and format instead of a manifestation link.
* **Rationale:** Prevents broken `/manifestation/null` links while keeping all user requests in one unified custodian triage interface.
