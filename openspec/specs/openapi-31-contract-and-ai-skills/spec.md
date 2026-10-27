# openapi-31-contract-and-ai-skills Specification

## Purpose
Complete 100% OpenAPI 3.1 specification, contract testing CI gate, AI skills, and collector Gemini Gem template.

## Requirements

### Requirement: Complete OpenAPI 3.1 Contract Coverage

The system SHALL emit a valid OpenAPI 3.1 document covering all registered API routes and schemas with accurate UUID field formats (`User.id`, `Item.owner_id`, `Notification.recipient_id`), faithful `PersonalAccessToken` (`is_active`, `revoked_at`) and `Notification` (`payload`, `actor_uri`) component schemas, Flask URL-converter-derived path parameter types, and decorator-backed authentication metadata (`_requires_auth`) so public routes are not falsely tagged as requiring Bearer authentication, and SHALL keep `docs/API.md`, `docs/CHANGELOG.md`, and `docs/gems/iqoqo-librarian-gem.md` synchronized with live route methods, paths, and wire payloads.

#### Scenario: CI validates zero contract drift

- **WHEN** `GET /api/docs/openapi.json` is generated and validated in CI (including when new routes or schemas are added)
- **THEN** unannotated routes fail CI validation, UUID fields declare `{"type": "string", "format": "uuid"}`, `PersonalAccessToken` and `Notification` schemas match their runtime `.to_dict()` representations, UUID/string path parameters are not mislabeled as integers, and public endpoints (`/api/auth/login`, `/api/federation/actor`, `/api/federation/directory`) omit mandatory Bearer security requirements

#### Scenario: Developer API documentation matches runtime 2FA, SSE, and OpenAPI routes

- **WHEN** a developer or AI agent consults `docs/API.md` and `docs/gems/iqoqo-librarian-gem.md`
- **THEN** `docs/API.md` documents `POST /api/auth/2fa/disable`, the two-step `POST /api/auth/login` MFA payload, accurate `/2fa/*` responses, unnamed `data: {...}` SSE frames, and `GET /api/docs/openapi.json`, while `iqoqo-librarian-gem.md` references `/api/scanner/preview/{barcode}` with matching PAT scopes
