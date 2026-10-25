## ADDED Requirements

### Requirement: 2FA Re-Enrollment Guard and PAT Privilege Isolation

The system SHALL prevent overwriting an already-enabled TOTP 2FA configuration via `POST /api/auth/2fa/enroll`, SHALL reject Personal Access Token (`iqo_*`) authentication on `/api/auth/tokens*` and `/api/auth/2fa/*` endpoints (`403 Forbidden`), SHALL restrict `"admin"` and `"*"` PAT scope creation to users holding the `"admin"` role, and SHALL enforce PAT scope checks in `@admin_required` and `@admin_or_custodian_required`.

#### Scenario: Attempting 2FA enrollment when already enabled

- **WHEN** an authenticated user with `totp_enabled == True` sends `POST /api/auth/2fa/enroll`
- **THEN** the endpoint returns `400 Bad Request` or `409 Conflict` without overwriting `totp_secret` or `totp_recovery_codes`

#### Scenario: Personal Access Token rejected on token and 2FA management endpoints

- **WHEN** a client authenticates using a Personal Access Token (`Authorization: Bearer iqo_...`) and calls `GET /api/auth/tokens`, `POST /api/auth/tokens`, `DELETE /api/auth/tokens/<id>`, or `/api/auth/2fa/*`
- **THEN** the endpoint returns `403 Forbidden`

#### Scenario: Read-only PAT belonging to admin rejected on admin endpoints

- **WHEN** an admin user authenticates with a PAT containing only `["read:catalog"]` and sends `GET /api/admin/users` (or any `@admin_required` route)
- **THEN** `@admin_required` returns `403 Forbidden` because `"admin"` / `"*"` is absent from `g.pat_scopes`

### Requirement: Frontend Login 2FA Challenge UI

The `/login` page (`frontend/app/login/page.tsx`) SHALL detect `{"mfa_required": true}` responses from `POST /api/auth/login`, render an input step for the 6-digit TOTP code or 8-character recovery code, and submit `{ email, password, otp_code }` to complete session authentication.

#### Scenario: User with 2FA enabled signs in via `/login`

- **WHEN** a user with 2FA enabled submits valid email and password on `/login`
- **THEN** the login form transitions to the two-factor verification prompt and completes `/api/auth-exchange` upon valid `otp_code` submission
