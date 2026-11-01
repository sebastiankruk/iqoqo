## Context

Commit `0f0d09d` on `origin/feat/1.0.0/mobile-capacitor` introduced `render_mobile_redirect()` in `app/api/auth.py`, returning a 150-line inline HTML/CSS document from Flask to trigger `iqoqo://auth-exchange?token=...`. Per our global rule **Flask Is API-Only; Never the Presentation Layer**, Flask (`app/`) must never serve HTML documents or hand-written CSS.

## Goals / Non-Goals

**Goals:**
- Deliver `Sign in with Apple` and mobile Google OAuth pass-through while keeping Flask 100% HTML-free.
- Support native email/password login, `v0.9.3` TOTP 2FA challenge completion, and `iqo_*` Personal Access Tokens in Capacitor.
- Handle both warm (`appUrlOpen`) and cold-start (`App.getLaunchUrl()`) `iqoqo://auth-exchange` deep links and clear stale React Query caches on token exchange.

**Non-Goals:**
- Rendering any HTML or CSS inside `app/api/auth.py`.

## Decisions

### Flask-Free Mobile OAuth Handoff via Frontend `/auth-exchange`
* **Decision:** When `mobile_origin=capacitor` is present in OAuth state, `app/api/auth.py` issues a standard HTTP 302 redirect to `${frontend_url}/auth-exchange?mobile=1#token=${internal_token}` (or `?token=...` with `Referrer-Policy: no-referrer` configured in `next.config.ts`). The Next.js frontend route `frontend/app/auth-exchange/page.tsx` detects whether it is running inside the native WebView (`isNativeApp()`) or an external system browser (`?mobile=1` on web): if native, it writes the token to `@capacitor-community/secure-storage`, clears `queryClient`, and calls `router.replace("/")`; if in the mobile system browser after OAuth, it renders a branded Shadcn card with `Navbar`/`Footer` that automatically opens `iqoqo://auth-exchange?token=...` and provides a fallback "Return to iqoqo App" button.
* **Rationale:** Strictly satisfies **Flask Is API-Only** and **Referrer-Policy: no-referrer** security rules while preserving reliable deep-link return on iOS Safari / Android Chrome Custom Tabs.

## Risks / Trade-offs

- **Risk:** Self-hosted instances without an Apple Developer account do not have `APPLE_CLIENT_ID` configured.
  - **Mitigation:** `Sign in with Apple` is optional at runtime: `GET /api/auth/providers` returns `{"google": bool, "apple": bool}`, the login/register UI only shows the Apple button when `apple: true`, and `/api/auth/login/apple` returns JSON `503` when unconfigured.
