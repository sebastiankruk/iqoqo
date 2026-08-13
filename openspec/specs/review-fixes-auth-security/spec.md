## ADDED Requirements

### Requirement: Allegro OAuth admin-only access
The `/api/auth/allegro/device-flow` and `/api/auth/allegro/device-token` endpoints SHALL require `@admin_required` authorization. Unauthenticated or non-admin users SHALL receive HTTP 403.

#### Scenario: Non-admin user attempts device flow

- **WHEN** a non-admin user sends POST to `/api/auth/allegro/device-flow`
- **THEN** the system SHALL return HTTP 403 Forbidden

### Requirement: Barcode preview rate limiting
The `/api/scanner/barcode-preview` endpoint SHALL enforce rate limiting of 30 requests per minute per IP and reject query strings exceeding 128 characters.

#### Scenario: Rate limit exceeded on barcode preview

- **WHEN** an IP sends more than 30 requests per minute to `/api/scanner/barcode-preview`
- **THEN** the system SHALL return HTTP 429 Too Many Requests

#### Scenario: Oversized query string

- **WHEN** a query string exceeding 128 characters is submitted to barcode preview
- **THEN** the system SHALL return HTTP 400 Bad Request
