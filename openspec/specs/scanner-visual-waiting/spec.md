# scanner-visual-waiting Specification

## Purpose
This specification defines the animated visual feedback shown to users during asynchronous scanner API lookups, including the escape mechanism for cancelling in-progress searches.

## Requirements

### Requirement: Visual Waiting Indicator
The scanner UI SHALL display a prominent animated overlay immediately upon image capture while awaiting API responses.

#### Scenario: Awaiting API response

- **WHEN** a user captures an image with the scanner
- **THEN** a high-visibility animated overlay appears until the data is returned or an error occurs.
