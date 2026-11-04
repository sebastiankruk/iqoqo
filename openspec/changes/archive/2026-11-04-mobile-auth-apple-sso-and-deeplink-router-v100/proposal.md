## Why
Native mobile apps cannot rely on `httpOnly` browser cookies across WebView boundaries and external OAuth system browsers (`ASWebAuthenticationSession` / Chrome Custom Tabs), and Apple App Store Guideline 4.8 mandates `Sign in with Apple` whenever third-party social login (Google OAuth) is offered. Furthermore, we must replace the inline HTML `render_mobile_redirect()` from `origin/feat/1.0.0/mobile-capacitor` (`0f0d09d`) to strictly honor our **Flask Is API-Only** architectural rule.

## What Changes

- **Linear Alembic Migration (`v1_0_0_add_apple_id_to_users`):** Add `apple_id = db.Column(db.String(255), unique=True, nullable=True, index=True)` to `User` (`app/db/auth.py`) chained linearly onto the `v0.9.4` head.
- **Sign in with Apple & Mobile OAuth Pass-Through (`app/api/auth.py`):** Add `/api/auth/login/apple` and `/api/auth/callback/apple` (optional when `APPLE_CLIENT_ID` is unset; advertised in `GET /api/auth/providers`). When `mobile_origin=capacitor` is passed to Google or Apple OAuth, redirect via HTTP 302 to `${frontend_url}/auth-exchange?mobile=1#token=...` (**zero HTML rendered by Flask**).
- **Mobile CORS, Bearer Token & TOTP 2FA Integration:** Allow `capacitor://localhost` and `https://localhost` in Flask CORS (`app/__init__.py`); ensure native `/login`, TOTP 2FA verification (`/api/auth/2fa/verify`), and PAT (`iqo_*`) Bearer auth store and clear tokens in `@capacitor-community/secure-storage` and invalidate TanStack Query caches on login/logout.
- **Client-Side `/auth-exchange` & Deep-Link Router (`navigation.ts`):** Create `frontend/app/auth-exchange/page.tsx` with `Referrer-Policy: no-referrer`: in native WebView, persists token to secure storage and routes to `/`; when opened in an external mobile browser after OAuth, renders a branded Shadcn UI card (`Navbar`, `Footer`, Tailwind tokens) that launches `iqoqo://auth-exchange?token=...`. Create `frontend/lib/capacitor/navigation.ts` (`App.addListener("appUrlOpen")` + `App.getLaunchUrl()` cold-start handler + Android hardware back button) preserving full `pathname + searchParams`.

## Capabilities

### New Capabilities
- `mobile-auth-apple-and-deeplinks`: Sign in with Apple OAuth, Flask-free mobile OAuth 302 redirect, client-side `/auth-exchange` page, and `iqoqo://` deep-link router with TOTP 2FA & PAT compatibility.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `app/db/auth.py`, `migrations/versions/*_v1_0_0_add_apple_id_to_users.py`
- `app/api/auth.py`, `app/config.py`, `app/__init__.py`, `.env.example`
- `frontend/app/auth-exchange/page.tsx`, `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`
- `frontend/lib/capacitor/navigation.ts`, `frontend/next.config.ts`
