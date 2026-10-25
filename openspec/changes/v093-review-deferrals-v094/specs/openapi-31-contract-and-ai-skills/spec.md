## MODIFIED Requirements

### Requirement: Complete OpenAPI 3.1 Contract Coverage

The system SHALL emit a valid OpenAPI 3.1 document covering all registered API routes and schemas without duplicate path declarations, and its documented schemas for `/api/auth/tokens` and `/api/auth/2fa/*` SHALL match the actual runtime JSON request/response payloads and HTTP status codes (`raw_token`, `expires_in_days`, and `200 OK` on revocation).

#### Scenario: CI validates zero contract drift

- **WHEN** A new route is added without OpenAPI parameter annotations
- **THEN** CI contract validation test fails.

#### Scenario: OpenAPI schema matches PAT creation and revocation runtime contract

- **WHEN** The OpenAPI 3.1 spec is generated at `/api/docs/openapi.json`
- **THEN** `POST /api/auth/tokens` documents `expires_in_days` in its request body and `raw_token` in its `201` response schema, and `DELETE /api/auth/tokens/{token_id}` documents its `200` response without duplicate path key overwrites in `app/api/docs.py`.

#### Scenario: Collector Gemini Gem uses valid catalog search parameters

- **WHEN** A collector configures the Gemini Gem using `docs/gems/iqoqo-librarian-gem.md`
- **THEN** The `/api/v1/catalog/search` operation documents the `q` query parameter supported by the backend endpoint.
