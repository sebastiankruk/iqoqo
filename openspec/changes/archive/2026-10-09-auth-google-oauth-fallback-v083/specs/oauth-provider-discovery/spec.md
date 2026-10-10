## Purpose

Allows unauthenticated client applications to discover active and configured authentication providers dynamically at runtime.

## ADDED Requirements

### Requirement: Query Active Authentication Providers
The system SHALL expose an unauthenticated public endpoint returning the runtime availability of third-party OAuth authentication providers.

#### Scenario: Discovering providers when Google OAuth is configured

- **WHEN** an unauthenticated client issues a GET request to `/api/auth/providers`
- **AND** Google OAuth client ID and secret are configured in instance settings or environment
- **THEN** the system returns HTTP 200 OK with `{"google": true}` in the JSON payload.

#### Scenario: Discovering providers when Google OAuth is not configured

- **WHEN** an unauthenticated client issues a GET request to `/api/auth/providers`
- **AND** Google OAuth client ID or secret is absent from instance settings and environment
- **THEN** the system returns HTTP 200 OK with `{"google": false}` in the JSON payload.

### Requirement: Dynamic Login Surface Adaptation
The client application SHALL dynamically suppress OAuth login and registration options when corresponding providers are disabled.

#### Scenario: Suppressing Google SSO button when disabled

- **WHEN** a user visits `/login` or `/register`
- **AND** `/api/auth/providers` reports `{"google": false}`
- **THEN** the user interface SHALL NOT render the "Sign in with Google" or "Sign up with Google" button.

#### Scenario: Displaying Google SSO button when enabled

- **WHEN** a user visits `/login` or `/register`
- **AND** `/api/auth/providers` reports `{"google": true}`
- **THEN** the user interface SHALL render the active Google SSO button.
