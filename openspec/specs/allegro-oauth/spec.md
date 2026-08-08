# allegro-oauth Specification

## Purpose
TBD - created by archiving change auth-and-integrations. Update Purpose after archive.
## Requirements
### Requirement: Allegro OAuth Authorization
The system MUST provide a UI-driven way to initiate the Allegro OAuth 2.0 Device Code flow, eliminating the need for manual SSH token generation and entry.

#### Scenario: Connecting an Allegro account

- **WHEN** the user provides the Client ID and Secret and clicks "Authorize Allegro" in the Instance Settings UI
- **THEN** the backend initiates the device code flow and returns a verification URL
- **THEN** the UI opens the verification URL in a new tab/window for the user to authenticate
- **THEN** the backend polls Allegro until authorization is complete and stores the access and refresh tokens securely
