## ADDED Requirements

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
