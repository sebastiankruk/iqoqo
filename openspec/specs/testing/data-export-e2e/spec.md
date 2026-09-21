## Purpose

Provides end-to-end test coverage for the user data sovereignty export workflow, ensuring users can successfully export their collections in multiple formats (JSON-LD, Turtle, JSON) with proper permission handling and error recovery.

## Requirements

### Requirement: E2E test for export button visibility and permissions
The system SHALL have an E2E test that validates the export button is visible to authenticated users with appropriate permissions and hidden from unauthorized users.

#### Scenario: Authenticated user sees export button

- **WHEN** authenticated user navigates to profile page
- **THEN** export button is visible and clickable

#### Scenario: Unauthenticated user cannot access export

- **WHEN** unauthenticated user attempts to access export endpoint
- **THEN** system redirects to login page

### Requirement: E2E test for format selection
The system SHALL have an E2E test that validates users can select different export formats (JSON-LD, Turtle, JSON) and the UI correctly reflects the selection.

#### Scenario: User selects JSON-LD format

- **WHEN** user clicks export and selects JSON-LD format
- **THEN** UI shows JSON-LD as selected format

#### Scenario: User selects Turtle format

- **WHEN** user clicks export and selects Turtle format
- **THEN** UI shows Turtle as selected format

#### Scenario: User selects JSON format

- **WHEN** user clicks export and selects JSON format
- **THEN** UI shows JSON as selected format

### Requirement: E2E test for download initiation
The system SHALL have an E2E test that validates the export process initiates a file download with the correct format and content.

#### Scenario: Successful export download

- **WHEN** user clicks export button with selected format
- **THEN** system initiates file download with correct file extension and content type

### Requirement: E2E test for visibility permissions
The system SHALL have an E2E test that validates export respects visibility permissions, excluding hidden items and including only public items.

#### Scenario: Hidden items excluded from export

- **WHEN** user exports collection with hidden items
- **THEN** exported data does not contain hidden items

#### Scenario: Public items included in export

- **WHEN** user exports collection with public items
- **THEN** exported data contains all public items

### Requirement: E2E test for large collection handling
The system SHALL have an E2E test that validates export handles large collections without timeout or memory errors.

#### Scenario: Export of 1000+ items

- **WHEN** user exports collection with 1000+ items
- **THEN** export completes successfully without timeout

### Requirement: E2E test for error handling
The system SHALL have an E2E test that validates proper error messages are displayed when export fails.

#### Scenario: Network error during export

- **WHEN** network error occurs during export
- **THEN** system displays user-friendly error message with retry option

#### Scenario: Invalid format selection

- **WHEN** user attempts export with invalid format
- **THEN** system displays validation error message
