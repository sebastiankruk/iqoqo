# backend-test-coverage

## Purpose

TBD

## Requirements

### Requirement: Entity audit logging is tested at the backend level

The system SHALL have pytest tests that verify entity audit log entries are created when merge operations and metadata edit operations occur.

#### Scenario: Audit log created on entity merge

- **WHEN** two FRBR entities are merged via the admin API
- **THEN** an audit log entry SHALL be created with the merge event type, source entity ID, and target entity ID

#### Scenario: Audit log created on metadata edit

- **WHEN** an FRBR entity's metadata is edited via the admin API
- **THEN** an audit log entry SHALL be created with the edit event type and the changed fields recorded

#### Scenario: Audit log is independent from custody log

- **WHEN** an entity audit log entry is created for a merge or edit event
- **THEN** the audit log entry SHALL NOT appear in the item custody event log

### Requirement: Item custody events are tested at the backend level

The system SHALL have pytest tests that verify item custody events are append-only, WEM records remain unmodified during custody operations, and loan request eligibility rules are enforced.

#### Scenario: Custody events are append-only

- **WHEN** a custody state change occurs (e.g., loan request, loan approval, return)
- **THEN** a new custody event record SHALL be appended to the custody log
- **THEN** existing custody events SHALL NOT be modified

#### Scenario: WEM records are unmodified during custody operations

- **WHEN** a custody event is recorded for a physical item
- **THEN** the associated Work, Expression, and Manifestation records SHALL remain unchanged

#### Scenario: Loan request eligibility for borrowable items

- **WHEN** a physical item is marked as borrowable
- **THEN** the API SHALL allow loan requests for that item

#### Scenario: Loan request ineligibility for non-borrowable items

- **WHEN** a physical item is NOT marked as borrowable
- **THEN** the API SHALL reject loan requests for that item

### Requirement: Cross-FRBR filtering edge cases are tested

The system SHALL have pytest tests that verify cross-FRBR filtering works correctly with 3 or more simultaneous filters from different taxonomies, AND logic combinations, and when no items match.

#### Scenario: Three simultaneous filters from different taxonomies

- **WHEN** filters for item status, item format, and item tags are applied simultaneously to a Works query
- **THEN** only Works whose associated items match ALL three filter conditions SHALL be returned

#### Scenario: AND logic for multiple tag filters

- **WHEN** multiple tag filters are applied (e.g., tags "horror" AND "classic")
- **THEN** only Works whose items have ALL specified tags SHALL be returned

#### Scenario: No matching items returns empty result

- **WHEN** filters are applied that no physical items match
- **THEN** the API SHALL return an empty result set with a 200 status

#### Scenario: Unauthenticated user sees correct counts

- **WHEN** an unauthenticated user requests filtered Works
- **THEN** the response SHALL include only publicly visible items in filter counts

### Requirement: Metadata refetch CLI script is tested

The system SHALL have pytest tests that verify the metadata refetch script (`scripts/refetch_metadata.py`) correctly handles gap detection, rate limiting, dry-run mode, force flag, and upsert logging.

#### Scenario: Gap detection identifies missing metadata

- **WHEN** the refetch script runs in gap-detection mode
- **THEN** items with missing metadata SHALL be identified and reported

#### Scenario: Rate limiting prevents API abuse

- **WHEN** the refetch script processes multiple items
- **THEN** requests to external metadata sources SHALL be spaced according to configured rate limits

#### Scenario: Dry-run mode makes no changes

- **WHEN** the refetch script runs with `--dry-run` flag
- **THEN** no metadata SHALL be written to the database
- **THEN** the script SHALL report what would have been changed

#### Scenario: Force flag overrides skip logic

- **WHEN** the refetch script runs with `--force` flag on an item that was already recently checked
- **THEN** the metadata SHALL be refetched regardless of the last-checked timestamp

#### Scenario: Never overwrite existing data

- **WHEN** an item already has metadata for a field
- **THEN** the refetch script SHALL NOT overwrite that field with external data

### Requirement: Format mapping CLI apply mode is tested

The system SHALL have pytest tests that verify the format mapping CLI (`scripts/fix_physical_kinds.py`) correctly handles apply/DML mode, dry-run, and error conditions.

#### Scenario: Apply mode updates physical kinds

- **WHEN** the fix_physical_kinds script runs in apply mode with valid mappings
- **THEN** physical item kinds SHALL be updated according to the format_mappings.yaml

#### Scenario: Dry-run mode reports without applying

- **WHEN** the fix_physical_kinds script runs with `--dry-run` flag
- **THEN** no physical item kinds SHALL be changed
- **THEN** the script SHALL report what would have been changed

#### Scenario: Invalid target error is handled

- **WHEN** the fix_physical_kinds script is given an invalid target kind
- **THEN** the script SHALL exit with a non-zero code and an error message

#### Scenario: Empty mappings yields warning

- **WHEN** format_mappings.yaml contains no entries
- **THEN** the script SHALL warn the user and exit without making changes

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
