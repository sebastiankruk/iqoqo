# semantic/sparql-api Specification

## Purpose

Provides a secure, read-only SPARQL 1.1 Protocol query interface and administrative explorer UI over the FRBR knowledge graph with user-scoped data filtering and strict operational guardrails.

## Requirements

### Requirement: Read-Only SPARQL 1.1 Protocol Endpoint

The system SHALL expose a read-only SPARQL 1.1 Protocol endpoint at `/api/sparql` that supports both HTTP GET and HTTP POST methods according to the W3C SPARQL 1.1 Protocol specification.

#### Scenario: Submitting SELECT query via HTTP GET

- **WHEN** an authenticated user issues a GET request to `/api/sparql` with a URL-encoded `query` parameter containing a valid SPARQL SELECT query
- **THEN** the system executes the query against the auth-scoped RDF graph and returns results in standard SPARQL JSON format (`application/sparql-results+json`) with HTTP status 200.

#### Scenario: Submitting SELECT query via HTTP POST with form encoding

- **WHEN** an authenticated user issues a POST request to `/api/sparql` with `Content-Type: application/x-www-form-urlencoded` and a `query` parameter containing a valid SELECT query
- **THEN** the system processes the query and returns results in SPARQL JSON format with HTTP status 200.

#### Scenario: Submitting SELECT query via HTTP POST with direct SPARQL query content

- **WHEN** an authenticated user issues a POST request to `/api/sparql` with `Content-Type: application/sparql-query` and the raw SPARQL query string as the request body
- **THEN** the system processes the query and returns results in SPARQL JSON format with HTTP status 200.

#### Scenario: Handling invalid SPARQL query syntax

- **WHEN** a request to `/api/sparql` contains a malformed SPARQL query string
- **THEN** the system rejects the request with HTTP status 400 Bad Request and provides a descriptive syntax error message in JSON.

### Requirement: Content Negotiation for Query Results

The system SHALL support standard content negotiation on `/api/sparql` via the HTTP `Accept` header for SPARQL query result and graph serializations.

#### Scenario: Requesting SPARQL XML or CSV format for SELECT queries

- **WHEN** an authenticated request sends an `Accept: application/sparql-results+xml` or `Accept: text/csv` header for a SELECT query
- **THEN** the system formats and returns the query result matching the requested MIME type with appropriate `Content-Type`.

#### Scenario: Requesting Turtle format for CONSTRUCT or DESCRIBE queries

- **WHEN** an authenticated request issues a SPARQL CONSTRUCT query with `Accept: text/turtle`
- **THEN** the system returns the serialized RDF graph in Turtle syntax with HTTP status 200.

### Requirement: Authentication and Authorization Enforcement

The system SHALL require valid user authentication on `/api/sparql` and restrict query execution based on caller session status.

#### Scenario: Rejecting unauthenticated SPARQL requests

- **WHEN** a client submits a GET or POST request to `/api/sparql` without a valid authentication session or token
- **THEN** the system rejects the request with HTTP status 401 Unauthorized.

### Requirement: Privacy and Auth-Scoped Graph Isolation

The system MUST construct an auth-scoped RDF graph preventing unauthorized access to private entity metadata.

#### Scenario: Public catalog visibility

- **WHEN** any authenticated user queries for Works, Expressions, and Manifestations
- **THEN** all published catalog entities are accessible and returned in the query results.

#### Scenario: Private user items excluded from other users

- **WHEN** user A executes a SPARQL query searching for Item or Custody entities
- **THEN** user A only receives results for their own private items and public items, and never sees private items belonging to user B.

### Requirement: Execution Guardrails and Resource Protection

The system SHALL enforce strict query execution limits including read-only validation, query size limits, auth-scoped graph limits, bounded result production, cancellable execution timeouts, and rate limits.

#### Scenario: Rejecting mutating SPARQL operations

- **WHEN** a query containing SPARQL 1.1 Update operations (such as INSERT, DELETE, LOAD, CLEAR, CREATE, or DROP) is submitted to `/api/sparql`
- **THEN** the system rejects the query before execution with HTTP status 400 Bad Request and an error indicating write operations are prohibited

#### Scenario: Enforcing query size limit

- **WHEN** a submitted query string exceeds 10 KB (10,240 bytes)
- **THEN** the system rejects the request immediately with HTTP status 413 Payload Too Large

#### Scenario: Enforcing execution timeout

- **WHEN** graph construction, graph serialization, child startup, query execution, or result serialization exceeds the configured five-second request budget
- **THEN** the system terminates isolated query work and returns HTTP status 504 without leaving runaway child processes

#### Scenario: Enforcing graph and result limits

- **WHEN** graph items/triples, SELECT bindings, CONSTRUCT/DESCRIBE triples, or serialized output exceeds its configured limit
- **THEN** the system stops production before unbounded memory accumulation and returns a controlled limit response

#### Scenario: Enforcing endpoint rate limiting

- **WHEN** a single authenticated user issues more than 10 SPARQL requests within a rolling 60-second window
- **THEN** the system rejects subsequent requests with HTTP status 429 Too Many Requests and a `Retry-After` header

#### Scenario: Handling isolated execution failure

- **WHEN** the isolated execution process exits without a valid result or IPC reaches its deadline
- **THEN** the system returns a structured 5xx or 504 JSON error and does not expose a traceback to the client

### Requirement: Admin SPARQL Query Explorer UI

The system SHALL provide an administrative SPARQL Query Explorer interface at `/admin/sparql` allowing administrators to inspect, execute, and export queries against the semantic catalog graph.

#### Scenario: Viewing default query interface and templates

- **WHEN** an authorized administrator navigates to `/admin/sparql`
- **THEN** the page displays an interactive query editor, a selector containing pre-configured example SPARQL queries, and an execution button.

#### Scenario: Executing query and viewing tabular results

- **WHEN** the administrator selects or inputs a SELECT query and clicks execute
- **THEN** the UI displays query results in a responsive data table showing variable headers, cell values, row count, and execution latency.

#### Scenario: Exporting query results to CSV and JSON

- **WHEN** query execution succeeds and the administrator clicks the download button
- **THEN** the UI initiates a client-side download of the current result set in the chosen format (CSV or JSON).

#### Scenario: Displaying query errors in UI

- **WHEN** a query execution fails due to syntax error or timeout
- **THEN** the UI displays an alert message detailing the failure reason without crashing the explorer interface.
