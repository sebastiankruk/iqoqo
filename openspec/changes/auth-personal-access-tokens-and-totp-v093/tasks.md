## 1. Personal Access Tokens (PATs)

- [ ] Create `PersonalAccessToken` model and migration `v0_9_3_pats`.
- [ ] Implement token generation, hashing, and decorator verification.
- [ ] Create PAT management UI in `frontend/components/profile/pat-management.tsx`.

## 2. TOTP 2FA Authentication

- [ ] Implement `pyotp` enrollment and login verification challenge in `app/api/auth.py`.
- [ ] Create TOTP setup wizard in `frontend/components/profile/totp-setup.tsx`.
- [ ] Write tests in `tests/test_auth_pat_and_totp.py` and `frontend/__tests__/components/profile/pat-and-totp.test.tsx`.

