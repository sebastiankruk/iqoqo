## ADDED Requirements

### Requirement: Declarative Role-Based Access Control on FRBR Mutations

The system SHALL strictly enforce authorization on all FRBR catalog mutation API routes using declarative decorators. Function-level implicit permission checks are prohibited for access control gating on top-level routes.

#### Scenario: Unauthorized user attempts to mutate catalog data

- **WHEN** an authenticated user without `write:metadata` permission attempts to PUT data to `/frbr/work/<id>`, `/frbr/expression/<id>`, `/frbr/manifestation/<id>`, or `/frbr/item/<id>`
- **THEN** the API SHALL return HTTP 403 Forbidden before executing any internal service logic.

### Requirement: Bounded Analytics Queries

Analytical queries spanning the entire user inventory SHALL be temporally bounded to prevent performance degradation through unbounded full table scans.

#### Scenario: Velocity stats calculation

- **WHEN** the system calculates collection velocity statistics
- **THEN** it SHALL restrict the dataset to items acquired within the last 12 months, allowing PostgreSQL to efficiently utilize date-based indexing.

### Requirement: IDOR Prevention on Item Target Escalations

The system SHALL verify ownership of private physical items before processing any escalation deletion request targeting an item.

#### Scenario: Custodian attempts to accept a deletion for an item they do not own

- **WHEN** a custodian attempts to accept a deletion request targeting an `item_id` not belonging to them
- **THEN** the system SHALL reject the operation and return HTTP 403 Forbidden.
