# mobile-oauth-and-origin-security Specification

## Purpose
Enforce cryptographic OAuth token/state verification, suspended-account and verified-email guards, single-use `POST` code exchange on mobile deep links, cross-server credential isolation, native server-side logout revocation, and non-credentialed Capacitor CORS compatibility.

## Requirements

### Requirement: Cryptographic Apple ID Token & Signed OAuth State Verification

The authentication API (`app/api/auth.py`) SHALL cryptographically verify Apple `id_token` RS256 signatures against Apple's published JWKS keys along with `iss` (`https://appleid.apple.com`), `aud` (`APPLE_CLIENT_ID`), and `exp` claims, and SHALL validate a mandatory HMAC-signed, time-bounded `state` parameter on OAuth callbacks.

#### Scenario: Forged or unsigned Apple `id_token` is rejected
- **GIVEN** Apple Sign-In is configured on the instance
- **WHEN** a client posts an unsigned, HS256-signed, wrong-audience, wrong-issuer, or expired `id_token` to `POST /api/auth/callback/apple`
- **THEN** the backend rejects the token and returns an HTTP 302 redirect to `/login?error=id_token_parse_failed` without creating or authenticating any user.

#### Scenario: Missing or tampered OAuth `state` is rejected on cross-site `form_post`
- **GIVEN** `POST /api/auth/callback/apple` is invoked without session cookies (cross-site `form_post`)
- **WHEN** `state` is missing, tampered, or older than 600 seconds
- **THEN** the backend fails closed and redirects to `/login?error=invalid_state`
- **AND WHEN** `state` carries a valid HMAC signature within TTL
- **THEN** the callback extracts `mobile_origin` and sanitized `callback_url` without requiring a `SameSite=Lax` cookie.

### Requirement: Suspended Account Enforcement & Verified Email Linking Across OAuth

All OAuth callbacks (`google_callback` and `apple_callback`, both web and `mobile_origin=capacitor`) SHALL reject deactivated users (`user.is_active == False`), SHALL look up provider subject IDs (`google_id` / `apple_id`) before case-insensitive email matching (`func.lower(User.email)`), and SHALL require `email_verified` to be truthy before linking an OAuth identity to an existing account.

#### Scenario: Suspended user attempts mobile OAuth bypass
- **GIVEN** a `User` with `is_active = False`
- **WHEN** that user completes Google or Apple OAuth with `mobile_origin=capacitor`
- **THEN** the callback does NOT mint a JWT or exchange code and redirects to `/login?error=account_suspended`.

#### Scenario: Unverified email cannot link to existing local account
- **GIVEN** an existing `User` with `email = "collector@example.com"` and `apple_id = None`
- **WHEN** `apple_callback` receives valid claims with `email = "Collector@example.com"` and `email_verified = False`
- **THEN** the backend refuses to link `apple_id` to the existing account and redirects with an authentication error.

### Requirement: Single-Use `OAuthExchangeCode` Handoff Without Raw JWTs in URLs

Mobile OAuth callbacks SHALL redirect with a short-lived, single-use `OAuthExchangeCode` (`?mobile=1&code=<code>`) rather than a raw JWT in the URL query or fragment, and `/auth-exchange` SHALL redeem codes exclusively via `POST` requests.

#### Scenario: Mobile OAuth handoff exchanges single-use code via POST
- **GIVEN** a mobile OAuth callback completes for an active user
- **WHEN** Flask redirects to `${frontend_url}/auth-exchange?mobile=1&code=<code>`
- **THEN** rendering `/auth-exchange` in the system browser does NOT consume `<code>` on `GET` and presents `iqoqo://auth-exchange?code=<code>`
- **AND WHEN** the native Capacitor WebView opens `/auth-exchange?code=<code>`
- **THEN** it sends `POST ${instanceUrl}/api/auth/exchange` with `{"code": "<code>"}`, stores the returned JWT in secure storage, clears TanStack Query cache, scrubs the URL via `history.replaceState`, and navigates to `/`.

### Requirement: Cross-Server Credential Purge & Native Logout Revocation

Switching to a different server URL in `ServerSelector` SHALL purge stored authentication tokens and clear the TanStack Query cache before activating the new instance, and logging out on native mobile SHALL revoke the active JWT on the server prior to local token deletion.

#### Scenario: Collector switches from primary server to third-party server
- **GIVEN** a mobile user authenticated on `https://server-a.example` with a stored Bearer token and cached items
- **WHEN** the user verifies and selects `https://server-b.example` in `ServerSelector`
- **THEN** `removeAuthToken()` and `queryClient.clear()` execute before subsequent requests, and zero requests to `https://server-b.example` carry Server A's `Authorization` header.

#### Scenario: Collector logs out from native mobile app
- **GIVEN** an authenticated native mobile user with a stored JWT
- **WHEN** the user triggers logout in `Navbar`
- **THEN** the app sends `POST ${instanceUrl}/api/auth/logout` with `Authorization: Bearer <jwt>` so the token `jti` is added to `TokenBlocklist` before local secure storage is cleared.

### Requirement: Non-Credentialed Native Mobile Requests & Default Capacitor CORS

Native Capacitor API requests SHALL set `withCredentials: false`, and the Flask backend SHALL permit non-credentialed CORS requests (`supports_credentials=False`) from `capacitor://localhost` and `https://localhost` on `/api/*` and `/.well-known/*` even when `CORS_ENABLED` is `false`.

#### Scenario: Native Android/iOS app connects to default self-hosted server (`CORS_ENABLED=false`)
- **GIVEN** a self-hosted iqoqo instance running with default `CORS_ENABLED=false`
- **WHEN** the Capacitor app (`Origin: https://localhost` or `Origin: capacitor://localhost`) sends preflight `OPTIONS` and `GET /api/public/u/alice` or `GET /api/items` with `withCredentials: false` and `Authorization: Bearer <token>`
- **THEN** the server responds with matching `Access-Control-Allow-Origin` and `Access-Control-Allow-Headers: Content-Type, Authorization` without `Access-Control-Allow-Credentials`.
