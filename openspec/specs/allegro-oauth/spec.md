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

### Requirement: Allegro Status Inspection & Healthcheck Accuracy
The status check tooling, Instance Settings UI, and system health endpoints SHALL accurately determine Allegro token lifecycle states — including persisted refresh-token rejection — and report diagnostic outcomes without false-positive active or authentication warnings.

#### Scenario: Active Allegro token reported as pass

- **WHEN** an operator runs `make status` (or `make status prod`)
- **AND** valid Allegro credentials and an active or refreshable token without a persisted refresh failure exist in instance settings
- **THEN** the status check outputs a passing check for Allegro API without warnings.

#### Scenario: Unconfigured Allegro credentials reported as info

- **WHEN** an operator runs `make status` on an instance without Allegro credentials configured
- **THEN** the status check outputs an informational note stating Allegro is not configured.

#### Scenario: Probe or database error reported distinctly from authentication failure

- **WHEN** the status script fails to connect to the database or execute the internal probe
- **THEN** the status check reports an explicit probe failure rather than claiming an OAuth handshake is pending.

#### Scenario: Persisted refresh failure reported as re-authorization required

- **WHEN** the stored Allegro token has a persisted refresh failure (`refresh_failed: true`, e.g., after `invalid_grant`)
- **THEN** `get_allegro_token_status()` SHALL return `allegro_token_active: false` and `reason: "reauth_required"` along with sanitized `refresh_error` and `refresh_failed_at` fields
- **AND** `make status` SHALL emit a warning instructing the operator to re-authorize Allegro in Instance Settings
- **AND** the Instance Settings UI SHALL display an explicit re-authorization warning state rather than an active state.

#### Scenario: Admin on-demand remote probe validates expired Allegro token

- **WHEN** an admin requests `GET /api/system/status?probe=true`
- **AND** the stored Allegro access token is expired and has a `refresh_token` without a prior `refresh_failed` flag
- **THEN** `get_allegro_token_status(probe_remote=True)` SHALL attempt a token refresh via `_refresh_user_token()`
- **AND** if Allegro rejects the refresh token with `invalid_grant`, the status response SHALL immediately return `allegro_token_active: false` and `reason: "reauth_required"`.

### Requirement: Bibliographic and Media Parameter Extraction from Allegro Catalog
The Allegro ingestion service SHALL parse structured catalog parameters from products and offers into canonical FRBR attributes, extracting creators, clean titles, publishers, and release years.

#### Scenario: Ingesting books and media with rich parameter structures

- **WHEN** an item is ingested or scanned via the Allegro Catalog API
- **THEN** the system SHALL parse parameter keys for `Autor`, `Autorzy`, `Wykonawca`, `Twórca`, `Reżyser`, clean `Tytuł`, `Wydawnictwo`, and `Rok wydania`
- **AND** the extracted values SHALL populate FRBR `work.meta["authors"]`, manifestation authors, publisher, and year
- **AND** display projections SHALL NOT fall back to "Undefined" or "Unknown Title".

### Requirement: Irreversible Allegro Refresh Failure Persistence and Short-Circuit
When Allegro rejects a `refresh_token` grant with a non-transient OAuth error (`400` with `error == "invalid_grant"` or `401`), the system SHALL persist the failure state on `ALLEGRO_TOKEN_DATA` and stop repeating doomed refresh requests until re-authorized.

#### Scenario: Refresh token rejected with invalid_grant

- **WHEN** `_refresh_user_token()` receives HTTP 400 with OAuth error `invalid_grant` (or HTTP 401) from `https://allegro.pl/auth/oauth/token`
- **THEN** the system SHALL update `ALLEGRO_TOKEN_DATA` in both cache and encrypted `InstanceSettings` with `refresh_failed: true`, `refresh_error` (e.g., `"invalid_grant"`), and `refresh_failed_at` (epoch timestamp)
- **AND** the system SHALL NOT delete `ALLEGRO_CLIENT_ID` or `ALLEGRO_CLIENT_SECRET`
- **AND** logs SHALL NOT expose the raw refresh token or JWT payload.

#### Scenario: Transient network or 5xx error does not poison token state

- **WHEN** `_refresh_user_token()` encounters a timeout, connection error, or HTTP 5xx response from Allegro
- **THEN** the system SHALL NOT set `refresh_failed: true`
- **AND** subsequent lookups MAY retry refreshing the token.

#### Scenario: Dead refresh token short-circuits repeated refresh attempts

- **WHEN** `get_allegro_token()` loads a token with `refresh_failed: true`
- **THEN** the system SHALL NOT send another `grant_type=refresh_token` POST request to Allegro
- **AND** `has_allegro_user_token()` SHALL return `false` so user-context-only endpoints (`/offers/listing`) are not called with a client-credentials token.

#### Scenario: Device Flow re-authorization clears refresh failure state

- **WHEN** an operator completes the Allegro Device Code flow and `save_allegro_token()` stores new tokens
- **THEN** `refresh_failed`, `refresh_error`, and `refresh_failed_at` SHALL be cleared from `ALLEGRO_TOKEN_DATA` in both cache and database
- **AND** `get_allegro_token_status()` SHALL return `allegro_token_active: true` and `reason: "active"`.

### Requirement: Allegro API Access Denial Diagnostic Logging
When Allegro catalog or listing endpoints reject requests with HTTP `401` or `403`, the system SHALL emit actionable warning diagnostics without exposing credentials or tokens.

#### Scenario: Allegro catalog or listing returns 403 AccessDenied

- **WHEN** `fetch_allegro_candidates()` receives HTTP `401` or `403` from `/sale/products` or `/offers/listing`
- **THEN** the system SHALL log a `WARNING` message including the endpoint path, HTTP status code, and token auth mode (`user_context` vs `client_credentials`)
- **AND** the log message SHALL NOT contain bearer tokens, client secrets, or raw authorization headers.
