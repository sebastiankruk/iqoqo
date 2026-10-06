## ADDED Requirements

### Requirement: Expression kind is mutable via admin API

The `expression.kind` attribute SHALL be exposed as a mutable field through the standard `PUT /api/admin/frbr/expression/{id}` endpoint. The endpoint SHALL accept `kind` in the request body and forward it to the service layer for validation and persistence. `expression.kind` SHALL NOT be a write-once ingestion artifact — it SHALL be correctable by admins through the same update path used for `content_type`, `language`, and `meta`.

#### Scenario: Kind forwarded alongside other expression fields

- **WHEN** an admin updates an Expression via `PUT /api/admin/frbr/expression/{id}` with `{"language": "en", "kind": "live_performance"}`
- **THEN** both the `language` and `kind` fields SHALL be updated on the Expression record

#### Scenario: Kind preserved when omitted

- **WHEN** an admin updates an Expression via `PUT /api/admin/frbr/expression/{id}` with `{"language": "pl"}` (no `kind` key in body)
- **THEN** the Expression's existing `kind` value SHALL remain unchanged
