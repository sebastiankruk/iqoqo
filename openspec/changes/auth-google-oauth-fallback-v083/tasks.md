## 1. Backend Provider Discovery

- [ ] 1.1 Implement `GET /api/auth/providers` in `app/api/auth.py` returning active provider dictionary based on `_ensure_google_oauth()`; verify with pytest in `tests/test_auth_providers.py`
- [ ] 1.2 Add pytest cases verifying unconfigured Google returns `{"google": false}` and configured returns `{"google": true}`

## 2. Frontend UI Integration

- [ ] 2.1 Create `useAuthProviders` client hook to fetch provider availability; verify with hook unit test
- [ ] 2.2 Update `frontend/app/login/page.tsx` to conditionally render Google SSO button only when `providers.google` is true; verify with Vitest
- [ ] 2.3 Update `frontend/app/register/page.tsx` to conditionally render Google SSO button only when `providers.google` is true; verify with Vitest
- [ ] 2.4 Add `oauth_not_configured` translation messages to `frontend/messages/en.json` and `frontend/messages/pl.json` and verify display when error query parameter is present
