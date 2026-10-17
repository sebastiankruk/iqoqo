## 1. User Model & Ingestion Integration

- [x] Add `default_item_visibility` column to `User` in `app/db/auth.py`.
- [x] Apply default in `app/api/items.py` and `app/api/scanner.py`.
- [x] Write tests in `tests/test_user_visibility_and_consent.py`.

## 2. Consent API & Frontend UI

- [x] Implement `/api/v1/profile/federation-consent` endpoints.
- [x] Cherry-pick `frontend/components/settings/federation-consent.tsx`.
- [x] Add Vitest tests in `frontend/__tests__/components/settings/federation-consent.test.tsx`.

