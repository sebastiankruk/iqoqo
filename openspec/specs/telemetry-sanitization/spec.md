# telemetry-sanitization Specification

## Purpose

Sanitize sensitive vendor authentication headers and handle oversized barcode telemetry records to prevent log pollution and information disclosure.

## Requirements

### Requirement: Expanded Telemetry Redaction
The system's OpenTelemetry hook MUST redact non-standard vendor authentication headers, specifically `Client-ID` and `Api-Key`, from outbound span attributes and application logs.

#### Scenario: IGDB/Twitch API request

- **WHEN** the backend makes an outbound HTTP request to the IGDB API containing a `Client-ID` header and an `Authorization: Bearer` header
- **THEN** the telemetry hook SHALL record both header values as `***REDACTED***` in the span attributes and logs.

#### Scenario: Standard headers are preserved

- **WHEN** the backend makes an outbound HTTP request containing a `Content-Type: application/json` header
- **THEN** the telemetry hook SHALL record the header value exactly as `application/json` without redaction.

### Requirement: Scan telemetry records oversized barcode rejections
The system SHALL record telemetry for oversized barcode submissions with `status='rejected_oversized'` instead of silently returning. The barcode value SHALL be truncated to 120 characters with a suffix indicating original length.

#### Scenario: Barcode exceeding 128 characters is submitted

- **WHEN** a barcode scan request contains a barcode string longer than 128 characters
- **THEN** the system SHALL record a `ScanTelemetry` entry with `status='rejected_oversized'`
- **AND** the `barcode` field SHALL contain the first 120 characters followed by `...(<original_length>)`
- **AND** the system SHALL log a warning with the original barcode length

#### Scenario: Normal-length barcode is submitted

- **WHEN** a barcode scan request contains a barcode string of 128 characters or fewer
- **THEN** the system SHALL record a `ScanTelemetry` entry with the original status (not `rejected_oversized`)
- **AND** the `barcode` field SHALL contain the full barcode value
