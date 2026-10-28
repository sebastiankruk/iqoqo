## Why
Enables programmatic API access for CLI tools/scripts and collector AI gems, while hardening administrator and contributor accounts with TOTP two-factor authentication.
## What Changes

- Add `auth.personal_access_tokens` table (`id`, `user_id`, `name`, `token_prefix`, `token_hash`, `scopes`, `expires_at`, `last_used_at`, `revoked_at`).
- Support PAT Bearer auth (`iqo_*`) in `app/api/decorators.py`.
- Implement TOTP 2FA enrollment, QR provisioning (`pyotp`), recovery codes, and login challenge in `app/api/auth.py`.
- Add PAT management and TOTP 2FA settings UI in `frontend/components/profile/`.

## Capabilities

### New Capabilities
- `auth-pat-and-totp`: Personal Access Tokens (PATs) with scoped bearer authorization and TOTP 2FA enrollment with recovery codes

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Expands authentication mechanisms, adds new auth tables, and profile security UI.
