# scanner-visual-waiting Specification

## Purpose
This specification defines the animated visual feedback shown to users during asynchronous scanner API lookups, including the escape mechanism for cancelling in-progress searches.

## Requirements

### Requirement: Visual Waiting Indicator
The scanner UI SHALL display a prominent animated overlay immediately upon image capture while awaiting API responses. The overlay SHALL include a user-accessible escape mechanism to cancel the lookup and proceed to manual entry.

#### Scenario: Awaiting API response

- **WHEN** a user captures an image with the scanner
- **THEN** a high-visibility animated overlay appears until the data is returned or an error occurs.

#### Scenario: User cancels during lookup

- **WHEN** a user clicks the "Skip and enter manually" button during the loading overlay
- **THEN** the overlay is dismissed immediately, the manual entry form is displayed with the last scanned barcode pre-filled, and no further API polling occurs for the cancelled request.
