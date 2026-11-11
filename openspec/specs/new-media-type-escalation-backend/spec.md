# new-media-type-escalation-backend Specification

## Purpose
Allow collectors to submit structured proposals for new media categories or physical formats through the Custodian escalation API without requiring an existing manifestation ID.

## Requirements

### Requirement: Structured `new_media_type` Escalation Requests

The escalation API (`POST /api/social/escalations`) SHALL accept `request_type="new_media_type"` with `manifestation_id=None` and a validated payload containing `proposed_category`, `proposed_format`, `parent_frbr_class`, `sample_identifier_or_url`, and `rationale`, and SHALL route the request to the Custodian queue with in-app notifications.

#### Scenario: Collector submits a request for a new media format

- **GIVEN** an authenticated collector wants to catalog a format not present in `shared/format_mappings.yaml`
- **WHEN** the user submits `POST /api/social/escalations` with `request_type="new_media_type"`, `proposed_category="video"`, `proposed_format="LaserDisc"`, and `rationale="12-inch optical video disc"`
- **THEN** the backend persists the `EscalationRequest` with `status="pending"`, notifies custodians, and returns HTTP 201.

### Requirement: Bounded `suggested_properties`, Rate Limiting, SQL Pagination, and OpenAPI 3.1 Schema (`M-03`, `M-06`)

`NewMediaTypeEscalationPayload`, escalation creation endpoints, and escalation listing endpoints MUST enforce input bounds, rate limits, SQL pagination, and OpenAPI 3.1 contract schemas.

#### Scenario: Reject oversized `suggested_properties` list or item strings

- **GIVEN** a `POST /api/escalations` (`request_type="new_media_type"`) request
- **WHEN** `suggested_properties` contains more than 20 items or an item exceeding 100 characters
- **THEN** the endpoint MUST reject the payload with HTTP `400 Bad Request`.

#### Scenario: Paginate `GET /api/escalations/mine` and `GET /api/escalations/queue` at the SQL level

- **GIVEN** a user or custodian querying `GET /api/escalations/mine?limit=50&offset=0` or `GET /api/escalations/queue?limit=50&offset=0`
- **WHEN** the query executes
- **THEN** SQL `LIMIT` and `OFFSET` MUST be applied in the database query rather than loading all rows into memory.
