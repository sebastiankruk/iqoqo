## Context

Currently, `EscalationRequest` (`app/db/social.py` / `app/api/social.py`) requires a target `manifestation_id` because existing escalations ask custodians to fix metadata or change the type of an already-ingested manifestation. When a collector wants to catalog a brand-new type of item not yet in `shared/format_mappings.yaml` (e.g., Postage Stamps, Trading Cards, VHS Tapes, LaserDiscs), no manifestation exists yet.

## Goals / Non-Goals

**Goals:**
- Allow authenticated users to submit `POST /api/social/escalations` (or `/api/v1/social/escalations`) with `request_type="new_media_type"` without requiring a `manifestation_id`.
- Validate the structured proposal (`proposed_category`, `proposed_format`, `parent_frbr_class`, `sample_identifier_or_url`, `rationale`) via Pydantic.
- Notify custodians via the `v0.9.2` In-App Notification Center (`C82`) and notify the requester upon resolution.

**Non-Goals:**
- Allowing non-admin users to dynamically mutate `shared/format_mappings.yaml` or `iqoqo.ttl` at runtime without ontology review.

## Decisions

### Extending `EscalationRequest` Rather Than Creating a Separate Table
* **Decision:** Reuse the `social.escalation_requests` table (allowing `manifestation_id` to be `NULL` when `request_type == "new_media_type"`) so all user-to-custodian requests appear in a single unified queue in `/profile` ("My Requests") and `/admin/content` ("User Requests").
* **Rationale:** Avoids duplicating status tracking, custodian resolution notes, and notification hooks.
