# scanner-error-fallback Specification

## Purpose
This specification defines the graceful degradation path from automated scanner lookups to manual barcode entry when API responses fail or time out.

## Requirements

### Requirement: Graceful Error Fallback
The scanner SHALL cleanly revert to a manual entry form upon lookup failure, pre-filling any successfully extracted metadata.

#### Scenario: API timeout

- **WHEN** the backend API lookup times out or fails
- **THEN** the UI dismisses the loading indicator and renders the manual entry form with the barcode pre-filled.

### Requirement: Lookup Timeout Parity

Frontend scanner lookup flows SHALL align their lookup timeout with the shared API client timeout (`15_000` ms) rather than enforcing a shorter hardcoded timeout that prematurely drops valid in-flight lookups into an empty manual entry form.

#### Scenario: Scanner lookup waits up to shared API client timeout

- **WHEN** a user scans or submits a barcode in the scanner page or bottom-sheet scanner
- **AND** the backend lookup takes between 10 and 15 seconds to resolve
- **THEN** the frontend SHALL wait for the shared API client timeout (`15_000` ms) instead of aborting at 10 seconds
- **AND** SHALL render the resolved metadata card upon response.

#### Scenario: Scanner lookup exceeds shared API client timeout

- **WHEN** a backend lookup exceeds the shared API client timeout (`15_000` ms)
- **THEN** the frontend SHALL cancel or ignore the timed-out lookup cleanly
- **AND** SHALL dismiss the loading indicator and revert to the manual entry form with the scanned identifier pre-filled.
