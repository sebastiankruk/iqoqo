## Purpose
Protects public-facing APIs from abuse and denial-of-service attacks by enforcing strict rate limits on incoming requests based on IP or user token.

## ADDED Requirements

### Requirement: Public API read endpoints are rate limited
The system SHALL limit requests to public-facing read APIs to a maximum of 60 requests per minute per client.

#### Scenario: Exceeding read limits
- **WHEN** a client makes more than 60 requests in a minute to a public read endpoint
- **THEN** the system returns a 429 Too Many Requests error response

### Requirement: Public API write endpoints are rate limited
The system SHALL limit requests to public-facing write APIs to a maximum of 30 requests per minute per client.

#### Scenario: Exceeding write limits
- **WHEN** a client makes more than 30 requests in a minute to a public write endpoint
- **THEN** the system returns a 429 Too Many Requests error response
