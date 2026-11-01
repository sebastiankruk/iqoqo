## 1. Frontend Settings UI Update

- [ ] 1.1 Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` items to `API_SERVICE_GROUPS` under Google Services in `frontend/components/admin/instance-settings.tsx`.
- [ ] 1.2 Verify `type: "api"`, placeholder strings, and labels for `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

## 2. Unit Testing & Verification

- [ ] 2.1 Add unit test in `frontend/__tests__/components/admin/instance-settings.test.tsx` verifying Google OAuth fields render, reveal on toggle, and trigger settings update.
- [ ] 2.2 Run frontend unit tests via `make test-frontend-unit` and format code with `make format-js` and `make lint`.
