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

### Requirement: Allegro OAuth polling is isolated in E2E verification
The Allegro OAuth E2E verification tests SHALL intercept the Allegro authentication polling endpoint and return a deterministic mock response instead of making external network requests.

#### Scenario: Allegro polling does not hang E2E verification

- **WHEN** the manual verification E2E test triggers a request matching `**/api/auth/allegro/**`
- **THEN** the test SHALL satisfy the request through its route interceptor
- **AND** the test SHALL remain deterministic without waiting for the external Allegro service
