# telemetry-sanitization Specification

## Purpose
TBD - created by archiving change sre-security-patches. Update Purpose after archive.
## Requirements
### Requirement: Expanded Telemetry Redaction

The system's OpenTelemetry hook MUST redact non-standard vendor authentication headers, specifically `Client-ID` and `Api-Key`, from outbound span attributes and application logs.

#### Scenario: IGDB/Twitch API request

- **WHEN** the backend makes an outbound HTTP request to the IGDB API containing a `Client-ID` header and an `Authorization: Bearer` header
- **THEN** the telemetry hook SHALL record both header values as `***REDACTED***` in the span attributes and logs.

#### Scenario: Standard headers are preserved

- **WHEN** the backend makes an outbound HTTP request containing a `Content-Type: application/json` header
- **THEN** the telemetry hook SHALL record the header value exactly as `application/json` without redaction.

