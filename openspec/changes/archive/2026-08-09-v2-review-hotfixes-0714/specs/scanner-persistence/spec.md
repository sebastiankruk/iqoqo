## ADDED Requirements

### Requirement: Oversized barcode telemetry recording

The system SHALL NOT silently drop scan telemetry for barcodes exceeding 128 characters. Instead, the system SHALL record the scan event with a truncated barcode value (first 120 characters plus a length indicator suffix) and a `status` of `'rejected_oversized'`, and SHALL log a warning.

#### Scenario: Barcode exceeds 128 characters

- **WHEN** `_record_scan_telemetry()` receives a barcode string longer than 128 characters
- **THEN** the system SHALL record a `ScanTelemetry` entry with `barcode` set to the first 120 characters followed by `"...(N)"` where N is the original length, and `status` set to `'rejected_oversized'`
- **AND** the system SHALL log a warning including the original barcode length

#### Scenario: Barcode within 128-character limit

- **WHEN** `_record_scan_telemetry()` receives a barcode string of 128 characters or fewer
- **THEN** the system SHALL record the telemetry entry with the full barcode value as before, with no truncation or special status
