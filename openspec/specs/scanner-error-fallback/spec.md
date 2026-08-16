# scanner-error-fallback Specification

## Purpose
TBD - created by archiving change release-0-7-15-scanner-ux. Update Purpose after archive.

## Requirements

### Requirement: Graceful Error Fallback
The scanner SHALL cleanly revert to a manual entry form upon lookup failure, pre-filling any successfully extracted metadata.

#### Scenario: API timeout

- **WHEN** the backend API lookup times out or fails
- **THEN** the UI dismisses the loading indicator and renders the manual entry form with the barcode pre-filled.
