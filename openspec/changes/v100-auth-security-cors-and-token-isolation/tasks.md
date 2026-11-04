## 1. Backend OAuth & CORS Security (`app/api/auth.py`, `app/__init__.py`)

- [x] 1.1 Implement Apple JWKS RS256 signature + `iss`/`aud`/`exp` verification (with bounded JWKS key caching and 5s timeout) in `app/api/auth.py` (`apple_callback`), removing `options={"verify_signature": False}`.
- [x] 1.2 Replace session-cookie-only OAuth state with `itsdangerous.URLSafeTimedSerializer` (`max_age=600`) carrying `{nonce, mobile_origin, callback_url}` in `google_login`/`google_callback` and `apple_login`/`apple_callback`, failing closed (`302 /login?error=invalid_state`) when `state` is missing, expired, or invalid.
- [x] 1.3 Enforce `if not user.is_active:` across all OAuth callbacks (closing `?mobile_origin=capacitor` bypass), require `email_verified` before linking existing accounts in `apple_callback`, query `google_id`/`apple_id` primary identifiers first, and normalize `func.lower(User.email) == email.strip().lower()` across `google_callback`, `apple_callback`, and `local_login`.
- [x] 1.4 Replace raw `#token=<jwt>` mobile OAuth redirects with single-use `OAuthExchangeCode` (`?mobile=1&code=<code>`), and ensure `POST /api/auth/exchange` supports JSON `{ "code": "..." }` returning `{ "access_token", "token_type" }` with `Cache-Control: no-store`.
- [x] 1.5 Update `app/__init__.py` CORS setup to always allow `capacitor://localhost` and `https://localhost` (`supports_credentials=False`, `allow_headers=["Content-Type", "Authorization"]`) on `/api/*` and `/.well-known/*` even when `CORS_ENABLED=false`, and remove `http://localhost` from credentialed `mobile_origins`.

## 2. Frontend Token Isolation, Logout, Auth Exchange & Open-Redirect Guards

- [x] 2.1 Set `config.withCredentials = false` inside `mobileRequestInterceptor` (`frontend/lib/api/client.ts`) whenever `isNativeApp()` is `true`.
- [x] 2.2 Update `ServerSelector` (`frontend/components/mobile/server-selector.tsx`) to call `await removeAuthToken()` and `queryClient.clear()` whenever switching to a different server URL, and warn/require confirmation for cleartext `http://` on non-loopback hosts.
- [x] 2.3 Update `handleLogout` in `frontend/components/dashboard/navbar.tsx` to call `await apiClient.post("/auth/logout")` on `isNativeApp()` *before* `removeAuthToken()` so server `TokenBlocklist` revokes the JWT `jti`.
- [x] 2.4 Refactor `frontend/app/auth-exchange/page.tsx` and `frontend/app/api/auth-exchange/route.ts` to use `POST` exclusively (no state-mutating `GET`), redeem `?code=` via `POST ${instanceUrl}/api/auth/exchange` on native and `POST /api/auth-exchange` on `"Continue in web browser"`, scrub query + hash via `history.replaceState(null, "", window.location.pathname)`, and call `queryClient.clear()`.
- [x] 2.5 Sanitize `callbackUrl` in `frontend/app/login/page.tsx` and path resolution in `frontend/lib/capacitor/navigation.ts` (`parseAppUrl`) to reject protocol-relative `//` open redirects; fix `frontend/app/register/page.tsx` (`resolveApiUrl("/auth/register")`, `minLength={8}`, `isLoading`, `try/catch`, `queryClient.clear()`, native token persistence); and mask unrevealed API inputs (`type="password"`) + add error toasts in `frontend/components/admin/instance-settings.tsx`.

## 3. Security & Regression Tests

- [x] 3.1 Expand `tests/test_auth_apple.py` and `tests/test_auth_google_mobile.py` to test forged/unsigned/wrong-aud/expired Apple JWT rejection, missing/tampered HMAC `state` rejection, cross-site `form_post` without session cookies, suspended-user (`is_active=False`) `mobile_origin=capacitor` rejection, unverified-email link rejection, case-insensitive email lookup, and single-use `?code=` redirect.
- [x] 3.2 Expand `tests/test_mobile_readiness.py` and `frontend/__tests__/lib/api/client.test.ts` to verify `withCredentials: false` on native requests and Capacitor CORS preflight success when `CORS_ENABLED=false` on both `/api/items` and `/api/public/*`.
- [x] 3.3 Add frontend unit/E2E tests in `server-selector.test.tsx`, `navbar.test.tsx`, `auth-exchange.test.tsx`, `login/page.test.tsx`, and `mobile_auth.spec.ts` covering cross-server token/cache purge, native logout revocation, `POST` code exchange, and open-redirect sanitization.
