## ADDED Requirements

### Requirement: Enforceable SPARQL Resource Isolation

The SPARQL endpoint MUST enforce resource limits that terminate or isolate expensive query work rather than merely timing out the HTTP request.

#### Scenario: Query exceeds execution deadline

- **WHEN** a query exceeds the configured execution deadline
- **THEN** the request returns the documented timeout response and no unbounded query work continues in the serving process

#### Scenario: Query produces excessive intermediate work

- **WHEN** a query creates a Cartesian product or intermediate result above the configured bound
- **THEN** execution is stopped or rejected with a structured resource-limit error before worker memory is exhausted

#### Scenario: Concurrent expensive requests

- **WHEN** multiple authenticated users submit expensive queries concurrently
- **THEN** a bounded concurrency policy prevents the endpoint from consuming all application workers or executor capacity

#### Scenario: Result row limit

- **WHEN** a SELECT query would return more than the configured row limit
- **THEN** the endpoint applies a bounded result policy during execution or rejects the query, rather than truncating only after an unbounded result has been materialized

### Requirement: Read-Only Operation Validation

The endpoint MUST accept valid read queries and reject SPARQL Update operations using operation-aware validation, while not rejecting the words `INSERT`, `DELETE`, or similar when they occur only in literals or comments.

#### Scenario: Read query contains update words as data

- **WHEN** a valid SELECT query contains the word `INSERT` in a literal or comment
- **THEN** the query is not rejected solely because of that word

#### Scenario: Update operation is submitted

- **WHEN** a client submits a valid SPARQL Update operation
- **THEN** the endpoint rejects it before execution with the existing write-rejection contract
