## MODIFIED Requirements

### Requirement: Complete OpenAPI 3.1 Contract Coverage

The system SHALL emit a valid OpenAPI 3.1 document covering all registered API routes and schemas without duplicate path declarations, and its documented schemas for `/api/auth/tokens`, `/api/auth/2fa/*`, `/api/items/{item_id}/reading-sessions`, `/api/public/share/{token}`, and `Expression.content_type` SHALL match the actual runtime JSON request/response payloads, query parameters (`page`, `per_page`, `format`, `limit`), and HTTP status codes (`raw_token`, `expires_in_days`, `201 Created` on reading sessions, and `200 OK` on revocation).

#### Scenario: CI validates zero contract drift

- **WHEN** A new route is added without OpenAPI parameter annotations
- **THEN** CI contract validation test fails.

#### Scenario: OpenAPI schema matches PAT creation and revocation runtime contract

- **WHEN** The OpenAPI 3.1 spec is generated at `/api/docs/openapi.json`
- **THEN** `POST /api/auth/tokens` documents `expires_in_days` in its request body and `raw_token` in its `201` response schema, and `DELETE /api/auth/tokens/{token_id}` documents its `200` response without duplicate path key overwrites in `app/api/docs.py`.

#### Scenario: Collector Gemini Gem uses valid catalog search parameters

- **WHEN** A collector configures the Gemini Gem using `docs/gems/iqoqo-librarian-gem.md`
- **THEN** The `/api/v1/catalog/search` operation documents the `q` query parameter supported by the backend endpoint.

#### Scenario: Developer API documentation matches runtime 2FA, SSE, and OpenAPI routes

- **WHEN** a developer or AI agent consults `docs/API.md` and `docs/gems/iqoqo-librarian-gem.md`
- **THEN** `docs/API.md` documents `POST /api/auth/2fa/disable`, the two-step `POST /api/auth/login` MFA payload, accurate `/2fa/*` responses, unnamed `data: {...}` SSE frames, and `GET /api/docs/openapi.json`, while `iqoqo-librarian-gem.md` references `/api/scanner/preview/{barcode}` with matching PAT scopes.

#### Scenario: OpenAPI schema documents v1.0.3 reading sessions, shared collection pagination, and cartographic map content type

- **WHEN** The OpenAPI 3.1 spec is generated at `/api/docs/openapi.json`
- **THEN** `POST /api/items/{item_id}/reading-sessions` documents `duration_minutes`, `pages_read`, and `note` in its request body and a `201` response, `GET /api/public/share/{token}` documents `page`, `per_page`, `format`, and `limit` query parameters, and `components.schemas.Expression.properties.content_type.enum` includes `"cartographic_map"`.
