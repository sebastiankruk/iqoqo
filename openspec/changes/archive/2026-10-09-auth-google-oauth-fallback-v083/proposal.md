## Why

Dev-note bug (#bugs #v083): "if Google not configured - logging with Google should be disabled". Release planning: v0.8.x, C54 (target v0.8.3).

Premises verified against code:
- **Confirmed: Unconditional SSO buttons in frontend.** `frontend/app/login/page.tsx:105-114` and `frontend/app/register/page.tsx:88-95` unconditionally render "Sign in with Google" / "Sign up with Google" buttons regardless of whether OAuth is configured.
- **Confirmed: Missing provider capabilities endpoint.** The backend has no unauthenticated endpoint for clients to discover enabled authentication providers. Credentials can be configured at runtime via `InstanceSettings` (stored in database and resolved via `ConfigService.get("GOOGLE_CLIENT_ID")`), so static build-time environment flags like `NEXT_PUBLIC_GOOGLE_AUTH_ENABLED` are brittle and out-of-sync with admin UI updates.
- **Confirmed: Backend error handling already redirects.** `app/api/auth.py:201-204` checks `_ensure_google_oauth()` and redirects to `/login?error=oauth_not_configured`. However, the user experience is jarring (redirect bounce) and `oauth_not_configured` lacks user-friendly handling in registration flows.

## What Changes

- **Backend API:** Expose unauthenticated `GET /api/auth/providers` on `auth_bp` returning active authentication providers and capabilities (e.g., `{"google": true|false}`). The response inspects runtime credentials via `ConfigService`.
- **Frontend Integration:** Add a React query hook / fetch helper (`useAuthProviders`) used by `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx` to conditionally render OAuth buttons only when active.
- **Frontend Error UX:** Add translation key and user-facing alert for `oauth_not_configured` in both English and Polish translation files.

## Capabilities

### New Capabilities

- `oauth-provider-discovery`: Exposes runtime OAuth provider availability via a lightweight public endpoint so client applications adapt login/registration surfaces dynamically.

### Modified Capabilities

None.

## Impact

- **Backend:** `app/api/auth.py` (adds `GET /providers` route, cached/lightweight check).
- **Frontend:** `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests:** Pytest for `/api/auth/providers` (configured vs unconfigured scenarios); Vitest component tests verifying button suppression when Google OAuth is inactive.
