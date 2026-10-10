# semantic/sparql-execution-service Specification

## Purpose

Provides a dedicated, internally authenticated and resource-limited execution boundary for SPARQL workloads so expensive queries cannot starve the primary web API.

## Requirements

### Requirement: Internally Authenticated SPARQL Execution Service

The system SHALL provide an internal-only service that accepts only authenticated, caller-scoped SPARQL execution requests from the main API.

#### Scenario: Authorized request is submitted

- **WHEN** the API submits a valid signed request containing a bounded graph scope and deadline
- **THEN** the service accepts the request, executes only that scope, and returns a correlated result

#### Scenario: Unauthenticated internal request is submitted

- **WHEN** a caller without valid internal credentials submits a request to the service
- **THEN** the service rejects it without executing the query

#### Scenario: Client attempts to select another tenant

- **WHEN** a request contains a user or graph scope that is not represented by the API-issued authorization context
- **THEN** the service rejects the request and does not access or return another user's private data

### Requirement: Service-Level Resource Governance

The service SHALL enforce bounded queue depth, concurrency, graph size, result size, CPU/memory/PID usage, and query deadlines independently of the web API workers.

#### Scenario: Service capacity is exhausted

- **WHEN** the queue or active-query budget is full
- **THEN** the service rejects or sheds the request with a controlled capacity response and does not create unbounded work

#### Scenario: Query exceeds its deadline

- **WHEN** isolated query work exceeds its deadline
- **THEN** the service terminates the work, cleans up its process resources, and returns a timeout result to the API

#### Scenario: Worker container exceeds a resource limit

- **WHEN** a worker reaches its configured CPU, memory, or process limit
- **THEN** the service remains restartable and the API reports service unavailability without affecting unrelated web requests

### Requirement: SPARQL Service Failure Observability

The service SHALL expose health, readiness, capacity, timeout, rejection, worker-restart, and resource-utilization signals without logging query text or private graph values.

#### Scenario: Operator checks service readiness

- **WHEN** the readiness endpoint is queried
- **THEN** it reports whether the service can accept authenticated execution requests and identifies dependency failures

#### Scenario: Query is terminated

- **WHEN** a query is terminated for timeout, limit, or resource exhaustion
- **THEN** metrics and structured logs record the reason, duration, and bounded sizes using a correlation identifier without sensitive query data
