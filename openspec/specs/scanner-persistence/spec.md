# scanner-persistence Specification

## Purpose

Maintain scanner UI state persistence and auditable telemetry logging.

## Requirements

### Requirement: Media Type Selection Persistence

The scanner UI SHALL remember the user's last selected media type and restore it across consecutive scan operations and page reloads.

#### Scenario: Sequential scanning of same media type

- **WHEN** a user selects `"music"` as the media type and successfully scans a barcode
- **THEN** the scanner UI SHALL retain `"music"` as the selected media type for the next scan.

#### Scenario: Persistence across page navigation

- **WHEN** a user selects `"video"` as the media type, navigates to the dashboard, and returns to the scanner
- **THEN** the scanner UI SHALL initialize with `"video"` selected instead of the system default.

### Requirement: Policy Selection Persistence

The scanner UI SHALL remember the user's last selected scanning policy (Inventory, Wishlist, Catalog) and restore it.

#### Scenario: Sequential wishlist scanning

- **WHEN** a user selects the "Add to Wishlist" policy and scans an item
- **THEN** the UI SHALL retain the "Add to Wishlist" policy for the next scan, preventing accidental inventory additions.

### Requirement: Oversized barcode telemetry recording

The system SHALL NOT silently drop scan telemetry for barcodes exceeding 128 characters. Instead, the system SHALL record the scan event with a truncated barcode value (first 120 characters plus a length indicator suffix) and a `status` of `'rejected_oversized'`, and SHALL log a warning.

#### Scenario: Barcode exceeds 128 characters

- **WHEN** `_record_scan_telemetry()` receives a barcode string longer than 128 characters
- **THEN** the system SHALL record a `ScanTelemetry` entry with `barcode` set to the first 120 characters followed by `"...(N)"` where N is the original length, and `status` set to `'rejected_oversized'`
- **AND** the system SHALL log a warning including the original barcode length

#### Scenario: Barcode within 128-character limit

- **WHEN** `_record_scan_telemetry()` receives a barcode string of 128 characters or fewer
- **THEN** the system SHALL record the telemetry entry with the full barcode value as before, with no truncation or special status
