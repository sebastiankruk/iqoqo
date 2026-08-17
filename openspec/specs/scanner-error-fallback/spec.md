# scanner-error-fallback Specification

## Purpose
This specification defines the graceful degradation path from automated scanner lookups to manual barcode entry when API responses fail or time out.

## Requirements

### Requirement: Graceful Error Fallback
The scanner SHALL cleanly revert to a manual entry form upon lookup failure, pre-filling any successfully extracted metadata.

#### Scenario: API timeout

- **WHEN** the backend API lookup times out or fails
- **THEN** the UI dismisses the loading indicator and renders the manual entry form with the barcode pre-filled.
