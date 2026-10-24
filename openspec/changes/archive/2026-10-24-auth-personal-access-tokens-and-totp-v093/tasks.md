## 1. Personal Access Tokens (PATs)

- [x] Create `PersonalAccessToken` model and migration `v0_9_3_pats`.
- [x] Implement token generation, hashing, and decorator verification.
- [x] Create PAT management UI in `frontend/components/profile/pat-management.tsx`.

## 2. TOTP 2FA Authentication

- [x] Implement `pyotp` enrollment and login verification challenge in `app/api/auth.py`.
- [x] Create TOTP setup wizard in `frontend/components/profile/totp-setup.tsx`.
- [x] Write tests in `tests/test_auth_pat_and_totp.py` and `frontend/__tests__/components/profile/pat-and-totp.test.tsx`.

