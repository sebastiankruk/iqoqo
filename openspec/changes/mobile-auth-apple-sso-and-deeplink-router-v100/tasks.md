## 1. Database Migration & Backend Apple/Mobile OAuth (`app/`)

- [ ] 1.1 Add `apple_id` column to `User` in `app/db/auth.py` and generate linear Alembic migration `.venv/bin/python -m alembic revision -m "v1_0_0_add_apple_id_to_users"` (`len(revision) <= 32`).
- [ ] 1.2 Add `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, and `APPLE_PRIVATE_KEY` to `app/config.py` and `.env.example`.
- [ ] 1.3 Implement `/api/auth/login/apple` and `/api/auth/callback/apple` in `app/api/auth.py`, expose `"apple"` capability in `GET /api/auth/providers`, and update Google/Apple OAuth callbacks to redirect `mobile_origin=capacitor` flows via HTTP 302 to `${frontend_url}/auth-exchange?mobile=1#token=...` (zero HTML in Flask).
- [ ] 1.4 Configure Flask CORS in `app/__init__.py` to permit `capacitor://localhost` and `https://localhost` / `http://localhost` origins for mobile WebViews.

## 2. Frontend `/auth-exchange` & Deep-Link Navigation (`frontend/`)

- [ ] 2.1 Implement `frontend/app/auth-exchange/page.tsx` with `Referrer-Policy: no-referrer` in `frontend/next.config.ts`, supporting Web cookie exchange, Native SecureStorage token persistence + `queryClient.clear()`, and mobile system-browser `iqoqo://auth-exchange` handoff using Shadcn UI components.
- [ ] 2.2 Implement `frontend/lib/capacitor/navigation.ts` (`registerBackButtonHandler` and `registerDeepLinkHandler` using `App.addListener("appUrlOpen")` + `App.getLaunchUrl()` cold-start handling, preserving full `pathname + searchParams`).
- [ ] 2.3 Update `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, and logout handlers to support native token storage, TOTP 2FA challenges on native, conditional `Continue with Apple` button, and server switching link.

## 3. Verification & Tests

- [ ] 3.1 Author backend tests in `tests/test_auth_apple.py`, `tests/test_auth_google_mobile.py`, and `tests/test_auth_native_token.py` (including assertion that no HTML is returned by `app/api/auth.py`).
- [ ] 3.2 Author frontend unit and E2E tests in `frontend/__tests__/app/auth-exchange.test.tsx`, `frontend/__tests__/lib/capacitor/navigation.test.ts`, and `frontend/__tests__/e2e/mobile_auth.spec.ts`.
- [ ] 3.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
