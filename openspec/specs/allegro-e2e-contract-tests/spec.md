# allegro-e2e-contract-tests Specification

## Purpose

Define Playwright E2E contract test coverage for the Allegro OAuth device flow, verifying initiation, token polling, and error handling without external network dependencies.

## Requirements

### Requirement: E2E test for Allegro device flow happy path
The system SHALL have a Playwright E2E test that exercises the complete Allegro device flow from UI initiation through successful token exchange, mocking external Allegro API responses at the network level.

#### Scenario: Successful device flow completion

- **WHEN** an admin user initiates the Allegro device flow from the settings page
- **AND** the external Allegro API is mocked to return a valid device code and verification URL
- **THEN** the UI SHALL display the device code and verification link
- **AND** after simulated token exchange, the UI SHALL show success confirmation

### Requirement: E2E test for Allegro device flow error handling
The system SHALL have Playwright E2E tests covering error scenarios for the Allegro device flow.

#### Scenario: Allegro API unavailable

- **WHEN** an admin user initiates the Allegro device flow
- **AND** the external Allegro API is mocked to return a network error
- **THEN** the UI SHALL display an error message indicating the flow could not be initiated
- **AND** the UI SHALL NOT enter a polling loop

#### Scenario: Invalid Allegro credentials

- **WHEN** an admin user initiates the Allegro device flow with invalid client ID/secret
- **AND** the external Allegro API is mocked to return a 401 Unauthorized
- **THEN** the UI SHALL display an authentication error message

#### Scenario: Expired device code during polling

- **WHEN** the device flow is initiated and the external Allegro API returns a valid device code
- **AND** the polling endpoint is mocked to return `expired_token` after several attempts
- **THEN** the UI SHALL display an expiration message and offer to retry
