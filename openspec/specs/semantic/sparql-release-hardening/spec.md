# semantic/sparql-release-hardening Specification

## Purpose

Provides reliable and bounded SPARQL execution for the 0.8.0 release without weakening the critical cancellation and isolation guarantee identified by the security review.

## Requirements

### Requirement: Safe RDF URI Construction

The system SHALL encode or reject user-controlled path and URL components before using them as RDF URI terms.

#### Scenario: Cover filename contains spaces

- **WHEN** a visible item has a cover filename containing spaces or other reserved URI characters
- **THEN** RDF graph construction and SPARQL example queries complete without an uncaught server error

#### Scenario: Invalid URI component cannot be encoded safely

- **WHEN** a URI component cannot be safely normalized
- **THEN** the graph builder omits or marks that optional relation and the API remains available with a structured diagnostic

### Requirement: Bounded SPARQL Execution Lifecycle

The system SHALL enforce graph, result, serialized-byte, concurrency, and end-to-end deadline limits across graph construction, isolated query execution, and response formatting. The system SHALL enforce a configurable limit on the number of Works loaded during graph construction to prevent memory exhaustion on catalogs with large Work counts.

#### Scenario: Query exceeds an execution budget

- **WHEN** a query or any execution phase exceeds its remaining deadline
- **THEN** all query child processes are terminated and the API returns a controlled timeout response without leaving running or zombie work

#### Scenario: Concurrent query capacity is exhausted

- **WHEN** the configured SPARQL concurrency budget is exhausted
- **THEN** the API rejects the request with a controlled capacity response and does not start another query process

#### Scenario: Result exceeds a format limit

- **WHEN** SELECT bindings, graph triples, or serialized response bytes exceed the configured limit
- **THEN** execution stops before unbounded accumulation and the API returns a controlled limit response

#### Scenario: Work count exceeds memory safety limit

- **WHEN** the catalog contains more Works than the configured `MAX_GRAPH_WORKS` limit
- **THEN** the graph builder SHALL load only up to the limit and log a warning, preventing memory exhaustion on catalogs with 100K+ Works

### Requirement: Reliable Isolated-Process Communication

The system SHALL detect child completion, failure, timeout, and exit status using deadline-aware IPC rather than queue-presence polling.

#### Scenario: Child returns a successful result

- **WHEN** an isolated query child sends a result before the deadline
- **THEN** the parent receives and validates the result, closes IPC resources, joins the child, and returns the negotiated response

#### Scenario: Child exits without a result

- **WHEN** an isolated query child exits or fails before sending a valid result
- **THEN** the API returns a structured server error and records the child exit reason without raising an uncaught framework exception

### Requirement: SPARQL Chaos Testing Under Resource Pressure

The system SHALL provide stress tests that verify SPARQL execution behavior under memory pressure, process crashes, and resource exhaustion scenarios.

#### Scenario: Child process experiences memory pressure

- **WHEN** a SPARQL child process is subjected to memory pressure approaching the configured limit
- **THEN** the parent process detects the condition, terminates the child gracefully, and returns a controlled error response without system-wide impact

#### Scenario: Repeated timeout floods

- **WHEN** multiple concurrent queries all exceed the timeout simultaneously
- **THEN** all child processes are terminated, resources are released, and the system remains available for subsequent requests
