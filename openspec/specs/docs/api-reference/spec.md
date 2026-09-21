## Purpose

Provides comprehensive API documentation for new endpoints introduced in v0.8.0, enabling developers to integrate with SPARQL, public Linked Data, and data export APIs.

## Requirements

### Requirement: API reference document exists
The system SHALL have an API reference at `docs/API.md` documenting all new endpoints.

#### Scenario: API reference exists

- **WHEN** developer looks for API documentation
- **THEN** `docs/API.md` exists and is accessible

### Requirement: SPARQL endpoint documented
The API reference SHALL document the `/api/sparql` endpoint with request/response formats.

#### Scenario: SPARQL API documented

- **WHEN** developer reads API reference
- **THEN** `/api/sparql` endpoint is documented with request format, response format, and examples

### Requirement: Public endpoints documented
The API reference SHALL document all `/api/public/*` endpoints.

#### Scenario: Public API documented

- **WHEN** developer reads API reference
- **THEN** all public endpoints (`/api/public/works/<id>`, `/api/public/expressions/<id>`, `/api/public/manifestations/<id>`) are documented

### Requirement: Data export endpoint documented
The API reference SHALL document the `/api/items/export` endpoint.

#### Scenario: Export API documented

- **WHEN** developer reads API reference
- **THEN** `/api/items/export` endpoint is documented with format options and response structure

### Requirement: Authentication requirements documented
The API reference SHALL document authentication requirements for each endpoint.

#### Scenario: Auth requirements documented

- **WHEN** developer reads API reference
- **THEN** authentication requirements are clear for each endpoint

### Requirement: Rate limits documented
The API reference SHALL document rate limits for each endpoint.

#### Scenario: Rate limits documented

- **WHEN** developer reads API reference
- **THEN** rate limits are documented for each endpoint

### Requirement: Content negotiation documented
The API reference SHALL document content negotiation options.

#### Scenario: Content negotiation documented

- **WHEN** developer reads API reference
- **THEN** content negotiation options (Accept headers) are documented

### Requirement: Error responses documented
The API reference SHALL document error responses and status codes.

#### Scenario: Error responses documented

- **WHEN** developer reads API reference
- **THEN** error responses and status codes are documented for each endpoint
