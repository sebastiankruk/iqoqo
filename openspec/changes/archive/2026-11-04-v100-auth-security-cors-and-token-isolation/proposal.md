## Why

Pre-release security review of `v1.0.0` (PR #392) identified three `CRITICAL` authentication/origin vulnerabilities and five `MODERATE` token-lifecycle gaps:
1. `app/api/auth.py` (`apple_callback`) decodes `id_token` with `verify_signature: False`, allows CSRF `state` bypass when session cookies or `state` are missing (including cross-site Apple `response_mode=form_post` dropping `SameSite=Lax` cookies), links existing accounts by unverified email, and bypasses `user.is_active` suspended-account enforcement whenever `?mobile_origin=capacitor` is passed to Google or Apple OAuth.
2. Mobile `ServerSelector` (`frontend/components/mobile/server-selector.tsx`) updates `INSTANCE_URL_KEY` without clearing `AUTH_TOKEN_KEY` or TanStack Query cache, causing `mobileRequestInterceptor` to exfiltrate the user's primary server Bearer JWT or `iqo_*` PAT to any newly selected server.
3. `apiClient` (`frontend/lib/api/client.ts`) sends `withCredentials: true` on native mobile while Flask (`app/__init__.py`) defaults `CORS_ENABLED=false` and `CORS_SUPPORTS_CREDENTIALS=false` (and serves wildcard `*` on `/api/public/*`), causing Android/iOS WebViews to reject self-hosted server connections and public routes.
4. Mobile OAuth redirects expose raw 7-day JWTs in URLs/deep links instead of single-use 60-second `OAuthExchangeCode`s; native logout (`navbar.tsx`) hits relative `/api/auth/logout` without Bearer auth and never revokes JWTs in `TokenBlocklist`; `/auth-exchange` uses state-mutating `GET` and fails on web fallback; `LoginPage` `callbackUrl` and `parseAppUrl` lack open-redirect sanitization; and `RegisterPage` has `/auth/register` 404 fallback and validation drift.

## What Changes

- **Cryptographic Apple OAuth & Stateless Signed `state` (`app/api/auth.py`):**
  - Verify Apple `id_token` RS256 signatures against Apple's JWKS (`https://appleid.apple.com/auth/keys` with cached `PyJWKClient` / SSRF-safe fetch) and enforce `iss == "https://appleid.apple.com"`, `aud == client_id`, and `exp`.
  - Replace session-cookie OAuth state with an HMAC-signed, time-bounded token (`itsdangerous.URLSafeTimedSerializer` keyed with `SECRET_KEY`, `max_age=600`) encoding `{nonce, mobile_origin, callback_url}`, failing closed whenever `state` is missing, expired, or tampered.
  - Enforce `if not user.is_active:` across all OAuth callbacks (web and mobile), require `email_verified` before email-based account linking in `apple_callback`, query `User.google_id` / `User.apple_id` primary identifiers before case-insensitive `func.lower(User.email)` across `google_callback`, `apple_callback`, and `local_login`.
  - Replace `#token=<jwt>` mobile redirects with single-use 60-second `OAuthExchangeCode` (`?mobile=1&code=<code_str>` -> `iqoqo://auth-exchange?code=<code_str>`), redeemed via `POST /api/auth/exchange`.
- **Cross-Server Token Isolation & Logout Revocation (`server-selector.tsx`, `navbar.tsx`):**
  - Purge `AUTH_TOKEN_KEY` (`removeAuthToken()`) and `queryClient.clear()` whenever `ServerSelector` switches to a different server origin, and warn/confirm before saving cleartext `http://` non-loopback servers.
  - Invoke `apiClient.post("/auth/logout")` on native mobile *before* `removeAuthToken()` so server `TokenBlocklist` revokes the JWT `jti`.
- **Native `withCredentials: false` & Capacitor CORS (`client.ts`, `app/__init__.py`):**
  - Set `config.withCredentials = false` in `mobileRequestInterceptor` when `isNativeApp()` is `true`.
  - Register `capacitor://localhost` and `https://localhost` (`supports_credentials=False`, `allow_headers=["Content-Type", "Authorization"]`) on `/api/*` and `/.well-known/*` in `app/__init__.py` independent of `CORS_ENABLED`, removing `http://localhost` from credentialed `mobile_origins`.
- **Frontend Auth Route Hardening (`auth-exchange/page.tsx`, `login/page.tsx`, `register/page.tsx`, `navigation.ts`, `instance-settings.tsx`):**
  - Exchange single-use `code` via `POST` (`POST ${instanceUrl}/api/auth/exchange` on native, `POST /api/auth-exchange` on web), scrub query/hash via `history.replaceState(null, "", window.location.pathname)`, and clear React Query cache.
  - Sanitize `callbackUrl` and `parseAppUrl` against `//` protocol-relative open redirects.
  - Fix `RegisterPage` URL resolution (`resolveApiUrl("/auth/register")`), `minLength={8}`, `isLoading`, `try/catch`, `queryClient.clear()`, and native token persistence; mask unrevealed API inputs (`type="password"`) and surface save error toasts in `InstanceSettings`.

## Capabilities

### New Capabilities
- `mobile-oauth-and-origin-security`: Cryptographic Apple JWKS verification, HMAC-signed OAuth `state`, single-use mobile exchange codes, cross-server token isolation, native logout revocation, and credential-free Capacitor CORS.

### Modified Capabilities
- None (refines `v1.0.0` mobile authentication and server-switching surfaces prior to release tag).

## Impact

- **Backend:** `app/api/auth.py`, `app/__init__.py`
- **Frontend:** `frontend/lib/api/client.ts`, `frontend/components/mobile/server-selector.tsx`, `frontend/components/dashboard/navbar.tsx`, `frontend/app/auth-exchange/page.tsx`, `frontend/app/api/auth-exchange/route.ts`, `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/lib/capacitor/navigation.ts`, `frontend/components/admin/instance-settings.tsx`
- **Tests:** `tests/test_auth_apple.py`, `tests/test_auth_google_mobile.py`, `tests/test_mobile_readiness.py`, `frontend/__tests__/components/mobile/server-selector.test.tsx`, `frontend/__tests__/app/auth-exchange.test.tsx`, `frontend/__tests__/lib/api/client.test.ts`
