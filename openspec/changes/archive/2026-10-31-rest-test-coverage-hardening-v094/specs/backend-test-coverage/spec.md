## ADDED Requirements

### Requirement: User library streaming export is verified via integration tests

The system SHALL have automated tests verifying user library streaming export endpoints across supported Linked Open Data and JSON formats, with authentication and input validation enforcement.

#### Scenario: User stream export supports json-ld, turtle, nt, and json formats

- **WHEN** an authenticated user requests `GET /api/items/export` or `GET /api/v1/items/export` with `?format=json-ld`, `?format=turtle`, `?format=nt`, or `?format=json`
- **THEN** the system SHALL return HTTP 200 with streamed chunked payload matching user-owned items

#### Scenario: User stream export rejects invalid formats with 400

- **WHEN** an authenticated user requests `GET /api/items/export?format=xml`
- **THEN** the system SHALL return HTTP 400 with an error payload listing valid formats

#### Scenario: User stream export enforces authentication

- **WHEN** an unauthenticated client requests `GET /api/items/export`
- **THEN** the system SHALL return HTTP 401 Unauthorized

### Requirement: Email verification request endpoint rate limiting and error handling are verified

The system SHALL have automated tests verifying email verification resend behavior, account-scoped rate limiting, and mail service failure responses.

#### Scenario: Verification request succeeds for unverified user

- **WHEN** an authenticated user with an unverified email posts to `/api/account/email/verification-request`
- **THEN** the system SHALL return HTTP 200 with a delivery confirmation message

#### Scenario: Verification request enforces three requests per hour rate limit

- **WHEN** an authenticated user makes more than 3 verification requests in an hour
- **THEN** the system SHALL return HTTP 429 Too Many Requests

#### Scenario: Verification request handles mail delivery failure with 503

- **WHEN** email delivery fails due to an unavailable mail relay
- **THEN** the system SHALL return HTTP 503 with an error message

### Requirement: Borrower loan status retrieval endpoint is verified

The system SHALL have automated tests verifying borrower-scoped active loan status lookups.

#### Scenario: Active loan request returns serialized details

- **WHEN** an authenticated borrower requests `GET /api/lending/items/<item_id>/loan-status` for an item with an active loan request
- **THEN** the system SHALL return HTTP 200 with the serialized loan request data

#### Scenario: Non-requested item returns null data

- **WHEN** an authenticated user requests `GET /api/lending/items/<item_id>/loan-status` for an item they have not requested
- **THEN** the system SHALL return HTTP 200 with `data: null`

### Requirement: Linked Open Data admin statistics and cleanup endpoints are verified

The system SHALL have automated tests verifying administrative LOD statistics queries, cleanup triggers, and role-based access control.

#### Scenario: Non-admin users are rejected from LOD admin endpoints

- **WHEN** a non-admin, non-curator user requests `GET /api/admin/lod/stats` or `POST /api/v1/admin/lod/cleanup`
- **THEN** the system SHALL return HTTP 403 Forbidden

#### Scenario: Admin receives LOD statistics breakdown

- **WHEN** an administrator or curator requests `GET /api/admin/lod/stats`
- **THEN** the system SHALL return HTTP 200 with total manifestations, linked manifestations, total links, and authority counts

#### Scenario: Admin triggers LOD cleanup dry-run

- **WHEN** an administrator posts to `/api/v1/admin/lod/cleanup` with `{"dry_run": true, "batch_size": 50}`
- **THEN** the system SHALL return HTTP 200 with cleanup task execution metrics

### Requirement: Static gallery image serving security is verified

The system SHALL have automated tests verifying static gallery asset serving and directory traversal prevention.

#### Scenario: Valid gallery image is served

- **WHEN** a client requests an existing gallery asset via `GET /api/static/gallery/<filename>`
- **THEN** the system SHALL return HTTP 200 with image content

#### Scenario: Directory traversal attempts are rejected

- **WHEN** a client requests a path containing `../` via `GET /api/static/gallery/`
- **THEN** the system SHALL return HTTP 404 Not Found or HTTP 400 Bad Request
