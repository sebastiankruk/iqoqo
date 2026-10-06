## MODIFIED Requirements

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
