## Purpose

Provides platform-wide technical debt resolution across database migrations, external integrations, user interface accessibility, and test suite execution to ensure data integrity, resilience, and test determinism.

## ADDED Requirements

### Requirement: Hierarchical Collection Cycle Detection
The system SHALL reject any collection creation or update operation that would introduce a cyclical reference in the parent-child collection hierarchy.

#### Scenario: Attempting to assign descendant as parent
- **WHEN** a client attempts to update a collection by setting its parent identifier to itself or to any of its current descendant collections
- **THEN** the system SHALL reject the request with a 400 Bad Request error and leave the existing hierarchy unchanged

#### Scenario: Valid parent collection update
- **WHEN** a client assigns a valid, non-cyclical ancestor collection as the parent
- **THEN** the system SHALL persist the hierarchy change successfully

### Requirement: Idempotent Database Migrations and Data Preservation
Database migration scripts SHALL execute idempotently without failure on re-runs, and destructive table drops SHALL verify data preservation in target partition schemas prior to removing tables.

#### Scenario: Re-running migration scripts
- **WHEN** database migration scripts are applied to an environment where schemas, indexes, constraints, or reference data already exist
- **THEN** the migrations SHALL complete successfully without raising duplicate key or duplicate column errors

#### Scenario: Verification prior to dropping legacy tables
- **WHEN** a cleanup migration attempts to drop legacy catalog tables from the public schema
- **THEN** the migration SHALL verify that all existing records have been fully transferred to the target schema before dropping the source tables

### Requirement: External Subprocess and HTTP Request Timeouts
All invocations of external command-line utilities and remote HTTP services SHALL enforce finite execution timeouts and process isolation to prevent process deadlocks and resource leaks.

#### Scenario: Storage synchronization subprocess timeout
- **WHEN** an external file synchronization command exceeds 30 seconds of execution time
- **THEN** the system SHALL terminate the subprocess, release the execution thread, and record a timeout failure in logs

#### Scenario: Cold-start AI vision inference timeout
- **WHEN** a cover extraction request queries an external or local vision inference service undergoing model initialization
- **THEN** the system SHALL maintain an execution timeout of at least 90 seconds before terminating the connection

### Requirement: Normalized External Provider Ingestion Schemas
Entity metadata retrieved from external ingestion services SHALL be transformed into a consistent uniform snake_case property structure before transmission to client applications or persistence.

#### Scenario: Ingesting third-party entity payload
- **WHEN** metadata is retrieved from an external book, movie, game, or music provider with vendor-specific attribute naming conventions
- **THEN** the system SHALL map all attributes into canonical snake_case property keys

### Requirement: Server-Rendered Entity Details with Sanitized Structured Data
FRBR manifestation and item detail pages SHALL render foundational content on the server and sanitize embedded JSON-LD scripts to prevent script execution vulnerabilities.

#### Scenario: Accessing manifestation detail route
- **WHEN** a client requests a manifestation detail URL
- **THEN** the server SHALL return server-rendered HTML containing entity metadata and safely escaped JSON-LD structured data

#### Scenario: Escaping structured data script termination sequences
- **WHEN** manifestation or item metadata contains strings mimicking HTML script closing tags
- **THEN** the rendered JSON-LD payload SHALL escape these tags to prevent script injection vulnerabilities

### Requirement: Public Profile Pagination and Atomic Item Creation
Public user collection profiles SHALL support pagination with concurrent data retrieval, and barcode scanning workflows SHALL support single-transaction creation of items and cover artifacts.

#### Scenario: Browsing public collection profiles
- **WHEN** a visitor loads a user profile containing multiple items
- **THEN** the system SHALL retrieve profile summary and item collection data in parallel, providing paginated results for collection listings

#### Scenario: Atomic item and cover creation
- **WHEN** a user captures an item barcode and cover image through the scanner interface
- **THEN** the system SHALL submit the item metadata and image payload as an atomic transaction that succeeds or rolls back as a single unit

### Requirement: Session-Scoped Test Schema Rollback Isolation
The automated test harness SHALL establish database schemas once per test session and isolate individual test cases through transaction rollback savepoints.

#### Scenario: Sequential test case execution
- **WHEN** an individual test case creates or modifies database entities and finishes execution
- **THEN** the test harness SHALL roll back the active transaction savepoint without dropping or recreating database tables

#### Scenario: Validating ontology SHACL shapes
- **WHEN** test suites execute SHACL graph validation across multiple test cases
- **THEN** the test harness SHALL use session-cached ontology shapes rather than re-parsing graph definition files on each test execution

### Requirement: Deterministic Test Assertions and Guarded State Reset Endpoints
Automated test assertions SHALL evaluate exact status codes and conditions rather than permissive unions, and administrative test-reset endpoints SHALL be disabled in production configurations.

#### Scenario: Requesting test state reset outside testing mode
- **WHEN** a client sends a request to the lending test state reset endpoint without explicit test authorization or in a production configuration
- **THEN** the system SHALL reject the request with 403 Forbidden or 404 Not Found

#### Scenario: Executing tag filter and dynamic scan assertions
- **WHEN** automated test suites execute tag facet filters or dynamic barcode scan tests
- **THEN** the tests SHALL assert deterministic HTTP status codes and exact set memberships
