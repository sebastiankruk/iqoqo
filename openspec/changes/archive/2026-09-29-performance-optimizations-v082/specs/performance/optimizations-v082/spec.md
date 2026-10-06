## Purpose

Defines behavioral and reliability requirements for performance optimizations across catalog listings, hierarchy operations, faceted navigation, data export, filter evaluation, and RESTful resource access.

## ADDED Requirements

### Requirement: Keyset Cursor Pagination for Manifestations
The system SHALL support keyset cursor-based pagination for manifestation listing via query parameters, returning an opaque cursor token and result slice without executing deep offset table scans, while preserving backward compatibility for page-and-offset pagination when cursor parameters are absent.

#### Scenario: Requesting initial page with limit
- **WHEN** an API client requests manifestations specifying a page size limit
- **THEN** the system returns the matching manifestation entities along with a `next_cursor` token for fetching the subsequent page

#### Scenario: Fetching subsequent page using cursor
- **WHEN** an API client requests manifestations supplying the `cursor` token received from a prior response
- **THEN** the system returns the next contiguous page of manifestations starting after the cursor without scanning preceding database records

#### Scenario: Fallback to offset pagination
- **WHEN** an API client requests manifestations using traditional `page` and `limit` parameters without a cursor
- **THEN** the system returns the requested page using offset-based pagination preserving existing API behavior

### Requirement: Recursive Hierarchy Cycle Detection and Lineage Traversal
The system SHALL execute collection parent-child cycle validation and hierarchical lineage traversal within a single recursive query execution rather than iterative sequential database queries per hierarchy depth.

#### Scenario: Validating valid parent collection hierarchy
- **WHEN** a user assigns a parent collection that does not introduce a circular reference
- **THEN** the system traverses the complete ancestor hierarchy in a single recursive query execution and applies the update

#### Scenario: Detecting circular collection references
- **WHEN** a user attempts to update a collection with a parent identifier that would create a cycle in the hierarchy tree
- **THEN** the system detects the cycle during recursive hierarchy traversal and returns an HTTP 400 validation error

### Requirement: Cached Ownership Facet Calculations
The system SHALL cache and efficiently evaluate user collection ownership facets (`owned`, `not_owned`) during faceted navigation statistics calculation to avoid redundant correlated subquery execution across multiple facet dimensions.

#### Scenario: Calculating faceted navigation stats with ownership filters
- **WHEN** an authenticated user requests faceted catalog statistics with an ownership filter applied
- **THEN** the system computes cross-filtered facet counts using cached or set-based ownership evaluation without executing correlated exists queries for each facet dimension

#### Scenario: Reusing cached ownership facet statistics
- **WHEN** a client repeats a faceted statistics query with unchanged filters within the cache TTL window
- **THEN** the system delivers precomputed facet counts directly from high-speed cache storage

### Requirement: Memory-Bounded Streaming Catalog Export
The system SHALL stream administrative catalog export data in chunked batches through an active HTTP response with bounded memory utilization rather than buffering the entire catalog dataset in application memory prior to transmission.

#### Scenario: Exporting full catalog data
- **WHEN** an administrator requests a catalog export via the admin export endpoint
- **THEN** the system streams JSON export chunks progressively with attachment headers, maintaining constant bounded memory usage regardless of catalog entity count

#### Scenario: Client disconnection during export
- **WHEN** a client disconnects or aborts the connection during an active streaming export
- **THEN** the system halts query streaming immediately and frees database cursor and connection resources

### Requirement: Unified Multi-Entity Catalog Filtering
The system SHALL evaluate catalog filters (content-type, format, tags, collections, genres, publishers, statuses, missing cover/id flags, ownership) through a unified filter abstraction ensuring identical filtering semantics and query behavior across listing and counting endpoints.

#### Scenario: Filtering across multiple FRBR levels
- **WHEN** a client submits compound filters spanning manifestation formats, expression content types, work genres, and item ownership
- **THEN** the system applies consistent join paths and filter clauses across both manifestation listing and facet counting endpoints

#### Scenario: Sanitizing and normalizing filter parameters
- **WHEN** a client supplies filter parameters containing special characters, whitespace, or comma-separated tokens
- **THEN** the system sanitizes and expands the parameters into canonical filter criteria consistently across all supported database dialects

### Requirement: Idempotent Read-Only ISBN Lookup
The system SHALL treat ISBN lookup requests as read-only operations that retrieve catalog or external provider metadata without modifying database state or initiating background processing during an HTTP GET request.

#### Scenario: Looking up metadata for an uncataloged ISBN
- **WHEN** a client executes an HTTP GET request for an ISBN that does not exist in local inventory
- **THEN** the system fetches external metadata and returns the details in the HTTP response without inserting Work, Expression, or Manifestation records into the database

#### Scenario: Looking up metadata for an existing manifestation
- **WHEN** a client executes an HTTP GET request for an ISBN existing in the local catalog
- **THEN** the system returns the existing metadata without executing database mutations or triggering background cover generation tasks

#### Scenario: Explicit manifestation creation via POST
- **WHEN** a client submits a valid ISBN creation request via an HTTP POST endpoint
- **THEN** the system creates and persists the Work, Expression, and Manifestation records and initiates background processing workflows
