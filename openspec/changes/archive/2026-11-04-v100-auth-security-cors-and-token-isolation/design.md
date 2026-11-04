## Context

During the Principal Review of `release/1.0.0` (PR #392), several compound security and origin-boundary issues emerged where web-centric assumptions (`SameSite=Lax` session cookies, `withCredentials: true`, single-origin `localStorage`/React Query state, relative `/api/auth/logout` fetches) collided with Capacitor's native WebView model (`https://localhost` on Android, `capacitor://localhost` on iOS, multi-server switching, and cross-site `form_post` callbacks from `appleid.apple.com`).

## Goals / Non-Goals

**Goals:**
- Cryptographically verify Apple `id_token`s against Apple's official JWKS keys (`RS256`, `iss`, `aud`, `exp`) with bounded key caching.
- Eliminate OAuth CSRF `state` bypasses while preserving cross-site Apple `response_mode=form_post` compatibility without weakening session cookie `SameSite` defaults.
- Ensure suspended accounts (`is_active=False`) and unverified emails cannot authenticate or hijack accounts on any OAuth flow.
- Eliminate raw 7-day JWTs from redirect URLs and `iqoqo://` deep links in favor of single-use 60-second `OAuthExchangeCode`s redeemed exclusively via `POST`.
- Guarantee zero cross-server credential or cache leakage when switching instances in `ServerSelector`, and ensure native logout revokes server-side JWT `jti` entries.
- Make native Capacitor requests work against default self-hosted iqoqo instances (`CORS_ENABLED=false`) and `/api/public/*` routes without enabling credentialed wildcard/localhost CORS.

**Non-Goals:**
- Changing web BFF `HttpOnly` cookie session behavior for desktop/mobile web browsers.
- Adding native iOS/Android vendor SDK sign-in plugins (system browser OAuth via `@capacitor/browser` + HTTP 302 redirect remains the canonical architecture).

## Decisions

### 1. Stateless HMAC-Signed OAuth `state` (`itsdangerous.URLSafeTimedSerializer`)
Apple's `response_mode=form_post` issues a cross-origin `POST` from `https://appleid.apple.com` to `/api/auth/callback/apple`. Browsers withhold `SameSite=Lax` Flask session cookies on cross-site `POST` requests, which previously caused `session.pop("oauth_apple_state", None)` to be `None` and motivated the broken `if saved_state and state:` guard.
- **Decision:** Sign `{ "n": secrets.token_urlsafe(16), "m": mobile_origin, "cb": sanitized_callback_url }` using `URLSafeTimedSerializer(secret_key, salt="iqoqo-oauth-state")` (`max_age=600`). In `apple_callback` (and as a verified fallback/primary state payload in `google_callback`), require `state` to be present and pass cryptographic signature + 600s TTL verification; reject missing/invalid/expired `state` with `302 /login?error=invalid_state`.

### 2. Single-Use `OAuthExchangeCode` for Mobile Deep-Link Handoff
- **Decision:** Both web and mobile OAuth callbacks mint a 60-second `OAuthExchangeCode` (`exchange_code = OAuthExchangeCode.issue(user.id)`).
  - Web redirects to `${frontend_url}/api/auth-exchange?code=${code}` (or `/auth-exchange?code=${code}` posting to `/api/auth-exchange`).
  - Mobile (`mobile_origin == "capacitor"`) redirects `302` to `${frontend_url}/auth-exchange?mobile=1&code=${code}` (`Referrer-Policy: no-referrer`, `Cache-Control: no-store`).
  - In system browser, `/auth-exchange` renders the `"Open iqoqo App"` button pointing to `iqoqo://auth-exchange?code=${code}` (**never** redeeming the single-use code on `GET` so mail/link previewers or the browser tab do not burn the code before the native app opens!). If the user explicitly clicks `"Continue in web browser"`, it submits `POST /api/auth-exchange` with `{ code }`.
  - Inside native Capacitor WebView, `/auth-exchange` redeems `{ code }` via `POST ${instanceUrl}/api/auth/exchange`, stores the returned `access_token` in `capacitor-secure-storage-plugin`, clears TanStack Query cache, scrubs URL params via `history.replaceState(null, "", "/auth-exchange")`, and navigates to `/`.

### 3. `withCredentials: false` on Native + Dedicated Non-Credentialed Capacitor CORS
- **Decision:** Native Capacitor requests carry `Authorization: Bearer <token>` and never rely on browser cookies. Setting `config.withCredentials = false` in `mobileRequestInterceptor` allows Flask to permit `Origins: ["capacitor://localhost", "https://localhost"]` with `supports_credentials=False` across `/api/*` and `/.well-known/*` even when `CORS_ENABLED=false` — making every self-hosted iqoqo container mobile-ready by default while keeping `http://localhost` out of credentialed CORS allowlists.

### 4. Strict Origin-Switch Credential Purge in `ServerSelector`
- **Decision:** Before `setInstanceUrl(normalized)` persists a new server URL, compare `normalized` with `await getInstanceUrl()`. If the previous URL is non-empty and differs from `normalized` (or unconditionally on explicit server switch), execute `await removeAuthToken()` and `queryClient.clear()`.

## Risks / Trade-offs

- **[Apple JWKS Network Fetch Latency / Outages]** -> Mitigation: Cache Apple's JWKS keys in-memory with a 1-hour TTL (`PyJWKClient(..., cache_keys=True, lifespan=3600)` or SSRF-safe `http_client` cache) and enforce a strict 5-second timeout, redirecting cleanly to `/login?error=id_token_parse_failed` on failure.
- **[Single-Use Code Expiration If User Waits >60s on Handoff Card]** -> Mitigation: Use a 120-second TTL on `OAuthExchangeCode` for mobile handoff so users tapping `"Open iqoqo App"` have ample time without leaving long-lived credentials in URLs.
