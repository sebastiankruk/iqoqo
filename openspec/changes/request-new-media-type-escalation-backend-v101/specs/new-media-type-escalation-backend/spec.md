## Purpose
Allow collectors to submit structured proposals for new media categories or physical formats through the Custodian escalation API without requiring an existing manifestation ID.

## ADDED Requirements

### Requirement: Structured `new_media_type` Escalation Requests

The escalation API (`POST /api/social/escalations`) SHALL accept `request_type="new_media_type"` with `manifestation_id=None` and a validated payload containing `proposed_category`, `proposed_format`, `parent_frbr_class`, `sample_identifier_or_url`, and `rationale`, and SHALL route the request to the Custodian queue with in-app notifications.

#### Scenario: Collector submits a request for a new media format
- **GIVEN** an authenticated collector wants to catalog a format not present in `shared/format_mappings.yaml`
- **WHEN** the user submits `POST /api/social/escalations` with `request_type="new_media_type"`, `proposed_category="video"`, `proposed_format="LaserDisc"`, and `rationale="12-inch optical video disc"`
- **THEN** the backend persists the `EscalationRequest` with `status="pending"`, notifies custodians, and returns HTTP 201.
