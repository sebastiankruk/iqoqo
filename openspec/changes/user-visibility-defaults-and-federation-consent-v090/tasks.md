## 1. User Model & Ingestion Integration

- [ ] Add `default_item_visibility` column to `User` in `app/db/auth.py`.
- [ ] Apply default in `app/api/items.py` and `app/api/scanner.py`.
- [ ] Write tests in `tests/test_user_visibility_and_consent.py`.

## 2. Consent API & Frontend UI

- [ ] Implement `/api/v1/profile/federation-consent` endpoints.
- [ ] Cherry-pick `frontend/components/settings/federation-consent.tsx`.
- [ ] Add Vitest tests in `frontend/__tests__/components/settings/federation-consent.test.tsx`.

