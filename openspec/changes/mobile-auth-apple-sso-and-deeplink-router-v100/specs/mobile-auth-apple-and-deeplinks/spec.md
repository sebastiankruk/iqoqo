## Purpose
Provide Sign in with Apple SSO, Flask-free mobile OAuth deep-link redirects, client-side `/auth-exchange` token persistence, and `iqoqo://` deep-link routing for Capacitor mobile apps.

## ADDED Requirements

### Requirement: Flask-Free Mobile OAuth Redirect & Sign in with Apple

The Flask backend (`app/api/auth.py`) SHALL support optional Sign in with Apple (`/api/auth/login/apple`, `/api/auth/callback/apple`) and `mobile_origin=capacitor` OAuth pass-through via standard HTTP 302 redirects to the Next.js `/auth-exchange` route, and SHALL NOT return rendered HTML documents.

#### Scenario: Mobile Google or Apple OAuth callback completes
- **GIVEN** an OAuth flow initiated with `mobile_origin=capacitor`
- **WHEN** `/api/auth/callback/google` or `/api/auth/callback/apple` succeeds
- **THEN** Flask returns an HTTP 302 redirect to `${frontend_url}/auth-exchange?mobile=1#token=<jwt>` without rendering inline HTML.

#### Scenario: Apple OAuth is unconfigured on a self-hosted instance
- **GIVEN** `APPLE_CLIENT_ID` is not set
- **WHEN** `GET /api/auth/providers` is requested
- **THEN** it returns `"apple": false` and `GET /api/auth/login/apple` returns HTTP 503 JSON.

### Requirement: Client-Side `/auth-exchange` & Full Query-Param Deep-Link Router

The frontend `/auth-exchange` page SHALL carry `Referrer-Policy: no-referrer`, persist tokens via `setAuthToken()` (`@capacitor-community/secure-storage`) on native platforms, clear the React Query cache, and `registerDeepLinkHandler` SHALL forward both `pathname` and `searchParams` for `iqoqo://` deep links on both warm and cold app starts.

#### Scenario: Deep link `iqoqo://auth-exchange?token=jwt-abc` opens the mobile app
- **GIVEN** the native app receives `iqoqo://auth-exchange?token=jwt-abc` via `appUrlOpen` or `getLaunchUrl()`
- **WHEN** `registerDeepLinkHandler` processes the URL
- **THEN** it pushes `/auth-exchange?token=jwt-abc` to the Next.js router, which stores `jwt-abc` in secure storage, clears the query cache, and redirects to `/`.
