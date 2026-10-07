## MODIFIED Requirements

### Requirement: Privacy and Auth-Scoped Graph Isolation

The system MUST construct or request an auth-scoped RDF graph preventing unauthorized access to private entity metadata, and MUST preserve that scope across the internal execution boundary.

#### Scenario: Public catalog visibility
- **WHEN** any authenticated user queries for Works, Expressions, and Manifestations
- **THEN** all published catalog entities are accessible and returned in the query results

#### Scenario: Private user items excluded from other users
- **WHEN** user A executes a SPARQL query searching for Item or Custody entities
- **THEN** user A only receives results for their own private items and public items, and never sees private items belonging to user B

#### Scenario: Internal service receives a scoped request
- **WHEN** the API delegates a query to the execution service
- **THEN** the service receives only a bounded scope or snapshot authorized for that caller and cannot broaden it using query parameters

### Requirement: Execution Guardrails and Resource Protection

The system SHALL enforce strict query execution limits including read-only validation, query size limits, auth-scoped graph limits, bounded result production, cancellable execution deadlines, distributed concurrency limits, and rate limits.

#### Scenario: Rejecting mutating SPARQL operations
- **WHEN** a query containing SPARQL 1.1 Update operations (such as INSERT, DELETE, LOAD, CLEAR, CREATE, or DROP) is submitted to `/api/sparql`
- **THEN** the system rejects the query before delegation with HTTP status 400 Bad Request and an error indicating write operations are prohibited

#### Scenario: Enforcing query size limit
- **WHEN** a submitted query string exceeds 10 KB (10,240 bytes)
- **THEN** the system rejects the request immediately with HTTP status 413 Payload Too Large

#### Scenario: Enforcing execution timeout
- **WHEN** delegated graph preparation, query execution, or result serialization exceeds the configured request deadline
- **THEN** the service terminates the work and the API returns HTTP status 504 without leaving runaway work

#### Scenario: Enforcing graph and result limits
- **WHEN** graph items/triples, SELECT bindings, CONSTRUCT/DESCRIBE triples, or serialized output exceeds its configured limit
- **THEN** the system stops production before unbounded memory accumulation and returns a controlled limit response

#### Scenario: Enforcing endpoint rate limiting
- **WHEN** a user or the service reaches its configured rolling rate, queue, or active-query limit
- **THEN** the system rejects subsequent requests with HTTP status 429 or 503 and communicates retry guidance

#### Scenario: Handling isolated execution failure
- **WHEN** the isolated execution process or service exits without a valid result or IPC reaches its deadline
- **THEN** the system returns a structured 5xx or 504 JSON error and does not expose a traceback to the client
