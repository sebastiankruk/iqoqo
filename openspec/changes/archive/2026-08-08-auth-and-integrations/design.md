## Context

The current integration with Allegro requires users to generate and provide SSH tokens manually. This is an insecure, clunky user experience. We need to trigger the existing OAuth 2.0 Device Code flow directly from the UI (`instance-settings.tsx`) to our backend (`auth.py` and `allegro.py`) without changing the underlying auth method. Additionally, we have an existing Twitch integration that needs to be formally tested and verified to ensure it behaves correctly.

## Goals / Non-Goals

**Goals:**

- Replace SSH token generation with a UI-driven initiation of the OAuth 2.0 Device Code flow for Allegro.
- Create the necessary UI components to input API keys, initiate the Device Code flow, and display the connection status.
- Ensure the backend can start the device flow, provide the verification URL to the frontend, and poll for the token securely.
- Write tests to verify the Twitch API integration.

**Non-Goals:**

- Changing the current auth process we use in Allegro (we keep the Device Code flow, just moving it to the UI).
- Rewriting the entire Allegro SDK or Twitch SDK (we are only updating the auth mechanisms and adding tests).

## Decisions

### 1. Allegro OAuth Flow

- **Decision**: The frontend (`instance-settings.tsx`) will accept the Client ID and Secret and call the backend to start the device flow. The frontend will open the returned verification URL in a new tab. The backend will poll Allegro until authorization is complete and save the tokens.
- **Rationale**: This avoids introducing a new callback-based OAuth flow and maintains the current working approach while significantly improving the user experience by eliminating SSH access requirements.

### 2. Twitch Testing

- **Decision**: We will write unit and integration tests for the Twitch API endpoints that mock external HTTP requests.
- **Rationale**: Testing against live external APIs in CI is flaky. Mocking the responses allows us to verify the integration logic reliably.

## Risks / Trade-offs

- [Risk] **Token expiration and refresh** → Mitigation: Ensure the OAuth implementation correctly stores and uses refresh tokens to maintain a persistent connection without requiring constant user re-authorization.
