## Why

`MOD-SEC-22` currently has no safe, consistent deletion-confirmation path for both password and OAuth-only users. This v0.8.3 change will confirm control of the account's verified email address before irreversible deletion, while explicitly treating mailbox control as distinct from fresh authentication.

**Target release:** v0.8.3.

## What Changes

- Establish and maintain a trustworthy verified-email state for user accounts, including verification of locally supplied addresses, use of a verified-email assertion from a validated OIDC identity, and invalidation of verification when an address changes.
- Require an authenticated user to initiate account deletion; send a clear confirmation email only to the verified email already associated with that account. Do not delete or anonymize data on request initiation.
- Add a short-lived, cryptographically random, user- and deletion-purpose-bound, single-use confirmation token. Store only a secure digest, invalidate older tokens on resend, and rate-limit issuance and confirmation attempts.
- Make email-link opening non-destructive for mail scanners. Require the user to authenticate as the account owner and explicitly submit a CSRF-protected confirmation before deletion.
- On successful confirmation, atomically consume the token and apply the existing account-deletion semantics, invalidate all credentials and sessions for the account, and notify the verified address. Deletion is immediate after explicit confirmation; no grace period is introduced.
- If an account has no verified email, do not provide a weaker deletion bypass. Require the user to add or verify an email address before starting deletion.

## Capabilities

### New Capabilities
- `account-deletion-confirmation`: Verified-email confirmation, secure deletion-request lifecycle, and account-wide credential invalidation before irreversible account deletion.

### Modified Capabilities
- None.

## Impact

- **Backend APIs and authentication:** account email verification, deletion request and confirmation endpoints, rate limiting, CSRF protections, credential/session invalidation, and safe error handling.
- **Database:** verified-email state and deletion-confirmation token/request storage, including migrations and cleanup of expired requests.
- **Email delivery and operations:** transactional email delivery configuration, deletion-request/completion templates, and deployment documentation for email configuration.
- **Frontend:** profile settings for verifying an email and initiating deletion, plus a clear, explicit confirmation state that handles scanner-safe links.
- **Testing:** unit, API, migration, and frontend coverage for email verification, token lifecycle, mail-scanner behavior, deletion semantics, and credential revocation.
