# external-api-telemetry Specification

## Purpose

TBD - created by archiving change capture-allegro-user-agent-telemetry. Update Purpose after archive.

## Requirements

### Requirement: Capture Outbound HTTP Headers in Telemetry

The system SHALL capture and attach HTTP request headers to OpenTelemetry spans, AND emit them as structured logs, when making requests to external APIs (e.g., Allegro).

#### Scenario: Capturing standard headers

- **WHEN** the backend makes an HTTP request to an external API (like Allegro)
- **THEN** it must add `http.request.header.user_agent` and `http.request.header.accept` to the active OpenTelemetry span AND emit a structured log containing these fields.

#### Scenario: Redacting sensitive headers

- **WHEN** the backend makes an HTTP request that includes an `Authorization` header
- **THEN** it must redact the header value (e.g., `***REDACTED***`) before attaching it as an attribute to the active OpenTelemetry span and structured log.
