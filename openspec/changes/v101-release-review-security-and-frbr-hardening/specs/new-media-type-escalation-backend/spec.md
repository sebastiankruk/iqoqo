# Delta Specification: Request New Media Type Escalation Backend (`C108c`)

## ADDED Requirements

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
