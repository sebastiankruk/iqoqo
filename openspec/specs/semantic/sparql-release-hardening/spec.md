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

The system SHALL enforce graph, result, serialized-byte, concurrency, and end-to-end deadline limits across graph construction, isolated query execution, and response formatting.

#### Scenario: Query exceeds an execution budget

- **WHEN** a query or any execution phase exceeds its remaining deadline
- **THEN** all query child processes are terminated and the API returns a controlled timeout response without leaving running or zombie work

#### Scenario: Concurrent query capacity is exhausted

- **WHEN** the configured SPARQL concurrency budget is exhausted
- **THEN** the API rejects the request with a controlled capacity response and does not start another query process

#### Scenario: Result exceeds a format limit

- **WHEN** SELECT bindings, graph triples, or serialized response bytes exceed the configured limit
- **THEN** execution stops before unbounded accumulation and the API returns a controlled limit response

### Requirement: Reliable Isolated-Process Communication

The system SHALL detect child completion, failure, timeout, and exit status using deadline-aware IPC rather than queue-presence polling.

#### Scenario: Child returns a successful result

- **WHEN** an isolated query child sends a result before the deadline
- **THEN** the parent receives and validates the result, closes IPC resources, joins the child, and returns the negotiated response

#### Scenario: Child exits without a result

- **WHEN** an isolated query child exits or fails before sending a valid result
- **THEN** the API returns a structured server error and records the child exit reason without raising an uncaught framework exception
