## MODIFIED Requirements

### Requirement: Graceful Error Fallback

The scanner SHALL cleanly revert to a manual entry form upon lookup failure, pre-filling any successfully extracted metadata. The specification Purpose section SHALL contain a clear, descriptive statement rather than placeholder text.

#### Scenario: API timeout

- **WHEN** the backend API lookup times out or fails
- **THEN** the UI dismisses the loading indicator and renders the manual entry form with the barcode pre-filled.
