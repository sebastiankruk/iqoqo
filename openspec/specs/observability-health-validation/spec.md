# observability-health-validation Specification

## Purpose
Specify system health check endpoints, deploy token authentication for analytical queries, and SQL-level drift verification.

## Requirements

### Requirement: Automated Observability Stack Health Verification

The system SHALL validate the health, connectivity, and data flow of the OpenObserve monitoring stack during `make status` and environment startup.

#### Scenario: OpenObserve status verification during make status execution

- **WHEN** developer runs `make status` or `make status STACK=prod`
- **THEN** system checks if OpenObserve and OTel Collector containers are running, validates API health/auth endpoints, and reports telemetry ingestion readiness.

### Requirement: Trace Authorization Header Sanitization

The backend OTel telemetry hooks SHALL sanitize `Authorization` headers, Bearer tokens, and sensitive credential parameters from exported Flask API and Celery worker spans before shipping to OpenObserve.

#### Scenario: Redacting authorization headers from HTTP traces

- **WHEN** an authenticated HTTP request containing an `Authorization` header is processed by the Flask API
- **THEN** the emitted trace span redacts the header value to `[REDACTED]` prior to OTLP collector ingestion.

### Requirement: Consistent OTLP Endpoint Routing

The docker compose files and environment configuration SHALL configure containerized services (Flask API, Celery worker, Next.js SSR, Nginx) to route OTLP HTTP metrics/traces/logs to the OTel Collector at port 4318 without port mapping conflicts.

#### Scenario: Containers pushing OTLP signals in production

- **WHEN** services are initialized in production docker-compose stack with `OTEL_TRACES_EXPORTER=otlp`
- **THEN** all container telemetry exports successfully reach the OTel collector on internal port 4318 without connection refusal errors.

### Requirement: Observability Documentation and Diagnostic SQL Accuracy

The system documentation in `docs/MONITORING.md` SHALL accurately describe all 8 instrumented layers, default port topologies, RUM token workflow, ad-blocker resilience, and provide functional SQL queries for OpenObserve diagnostics.

#### Scenario: Reviewing OpenObserve diagnostic queries

- **WHEN** an SRE consults `docs/MONITORING.md` or SRE expert guidelines
- **THEN** the provided ANSI SQL queries for 5xx errors, worker tracebacks, and container resource metrics execute without syntax or schema errors against OpenObserve endpoints.
