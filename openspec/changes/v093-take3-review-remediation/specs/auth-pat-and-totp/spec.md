## MODIFIED Requirements

### Requirement: Personal Access Token Authentication

The system SHALL authenticate API requests using hashed Personal Access Tokens bearing the `iqo_` prefix via the `Authorization: Bearer` header, throttle `last_used_at` database writes to at most once every 60 seconds across both required-authentication and optional-authentication endpoints, enforce `read:catalog` (or `read:*`, `admin`, `*`) scope validation before authenticating optional-auth read requests, support `"curator"` scope creation for `contributor`, `custodian`, and `admin` roles, honor `"sparql:query"` on `POST /api/sparql` and `"write:inventory"` on item inventory mutations, and reject bearer credentials supplied via `?token=` URL query parameters.

#### Scenario: Valid PAT grants scoped access

- **WHEN** repeated requests arrive within 60 seconds carrying `Authorization: Bearer iqo_...` with `read:catalog` scope on either required-auth or optional-auth endpoints
- **THEN** the requests succeed and `last_used_at` is committed at most once per 60-second window

#### Scenario: PAT lacking read scope does not authenticate optional-auth catalog queries

- **WHEN** a request to an optional-authentication endpoint arrives with `Authorization: Bearer iqo_...` containing only `["sparql:query"]` (without `read:catalog`, `admin`, or `*`)
- **THEN** the endpoint does not authenticate the caller as the token owner or expose the owner's private or friends-only items

#### Scenario: Scoped PATs succeed on SPARQL, inventory, and curator endpoints

- **WHEN** a user authenticates with a `"sparql:query"` PAT on `POST /api/sparql`, a `"write:inventory"` PAT on item mutation routes, or a `"curator"` PAT (minted by a custodian/contributor) on custodian endpoints
- **THEN** each endpoint authorizes the request according to its matching scope while rejecting out-of-scope operations with `403 Forbidden`

#### Scenario: Query-string token parameter is rejected on SSE stream

- **WHEN** a client requests `GET /api/v1/events/stream?token=<jwt_or_pat>` without an `HttpOnly` session cookie or `Authorization: Bearer` header
- **THEN** the endpoint rejects the query-string credential with `401 Unauthorized` so bearer secrets are not accepted in access-logged URLs

### Requirement: TOTP Two-Factor Challenge

The system SHALL require a valid 6-digit TOTP code or single-use recovery code during login for enrolled accounts, reject replayed TOTP codes within their 90-second acceptance window in compliance with RFC 6238, rate-limit `POST /api/auth/2fa/enroll` and repeated OTP verification failures without blocking normal two-step MFA logins, and record audit log entries whenever 2FA is enabled or disabled.

#### Scenario: Login challenge requires OTP

- **WHEN** a user with 2FA enabled provides a valid username and password to `POST /api/auth/login`
- **THEN** the endpoint returns `200` with `mfa_required=True` prompting for a TOTP or recovery code

#### Scenario: Replayed TOTP code within the same acceptance window is rejected

- **WHEN** an attacker or client submits a 6-digit TOTP code that was already accepted for that user within the active 90-second verification window
- **THEN** `POST /api/auth/login` rejects the replayed code with `401 Unauthorized`

#### Scenario: Enabling or disabling 2FA writes an audit log entry

- **WHEN** an authenticated user completes 2FA verification (`/api/auth/2fa/verify`) or disables 2FA (`/api/auth/2fa/disable`)
- **THEN** the backend records an audit log entry capturing the user and the 2FA lifecycle transition

## ADDED Requirements

### Requirement: Canonical Frontend Origin Validation and Localized Auth UI

The Next.js BFF authentication exchange route (`/api/auth-exchange`) SHALL validate forwarded host headers using strict URL parsing—rejecting credentials/userinfo (`@`), paths (`/`), query strings (`?`), fragments (`#`), commas, and backslashes—before constructing redirect URLs, and the frontend authentication and `/profile` security interfaces SHALL hide privileged PAT scopes (`admin`, `*`) from non-admin users, localize all `PatManagement` and `TotpSetup` labels in English and Polish, and display inline login/MFA errors without duplicate browser alert dialogs.

#### Scenario: Spoofed X-Forwarded-Host with authority userinfo or path suffix cannot trigger Open Redirect

- **WHEN** a request arrives at `/api/auth-exchange` with `X-Forwarded-Host: iqoqo.cc:80@evil.example.com` or `X-Forwarded-Host: evil.example.com/.iqoqo.cc`
- **THEN** the route rejects the untrusted forwarded host header and redirects strictly to the configured trusted frontend origin

#### Scenario: Non-admin user views localized PAT and TOTP profile settings

- **WHEN** a non-admin user views `/profile` in English (`en`) or Polish (`pl`)
- **THEN** `PatManagement` and `TotpSetup` render localized text in the active locale and `PatManagement` omits the `admin` and `*` scope options
