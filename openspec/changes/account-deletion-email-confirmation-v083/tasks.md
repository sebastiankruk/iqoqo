## 1. Verified Email Identity

- [x] 1.1 Add a persisted email-verification state and reversible migration; verify existing addresses default to unverified unless trusted verification evidence exists, with migration tests
- [x] 1.2 Implement local email-verification issuance and confirmation using purpose-bound expiring single-use tokens, and verify valid, expired, replayed, and changed-address cases
- [x] 1.3 Trust federated email only when a validated OIDC response asserts `email_verified`; verify missing/false claims do not mark an address verified
- [x] 1.4 Invalidate email verification and pending email/deletion tokens whenever an account email changes, and verify with account-email lifecycle tests

## 2. Transactional Email Delivery

- [x] 2.1 Add a configurable TLS-protected SMTP mail-delivery boundary and verification/deletion email templates, and verify delivery using a test capture transport
- [x] 2.2 Use a configured trusted public application origin for generated links, redact tokens/URLs from logs, and verify hostile Host headers and logging do not leak token material
- [x] 2.3 Document required self-hosted mail settings and safe behavior when mail delivery is unavailable, and verify config tests and documentation examples

## 3. Deletion Request and Confirmation Lifecycle

- [x] 3.1 Add persisted deletion-request/token lifecycle with 32-byte-or-greater random tokens, digest-only storage, account/purpose binding, 30-minute expiry, resend invalidation, and cleanup; verify model and migration tests
- [x] 3.2 Implement authenticated, rate-limited deletion initiation to the account's verified email with a non-enumerating response and no deletion side effect; verify initiation, missing-email, rate-limit, and notification tests
- [x] 3.3 Implement a scanner-safe confirmation-link GET and explicit confirmation UI with no third-party resources and a `no-referrer` policy; verify repeated GET/prefetch does not mutate or consume the request
- [x] 3.4 Implement final confirmation requiring a valid token and authenticated session for the same account, with CSRF protection for cookie sessions; verify wrong-user, invalid-CSRF, and expired-token cases
- [x] 3.5 Make token consumption and existing account deletion atomic and single-use under concurrent requests, and verify rollback and replay behavior

## 4. Credential Revocation and Notifications

- [x] 4.1 Update protected authentication to reject credentials for missing or inactive users, and verify previously issued bearer and cookie JWTs fail after account deletion
- [x] 4.2 Queue or deliver request and completion notifications without exposing confirmation tokens, and verify delivery retry/failure does not partially delete or restore an account
- [x] 4.3 Verify account deletion preserves the current cascade/anonymization behavior, is immediate only after explicit confirmation, and has no post-confirmation grace period

## 5. Frontend and Security Verification

- [x] 5.1 Add profile email-verification and deletion-request states, clear permanent-deletion warnings, and pending-request messaging; verify frontend component tests
- [x] 5.2 Add security tests for token purpose/expiry/replay/supersession, rate limits, scanner behavior, CSRF, concurrent confirmation, and token/log/referrer leakage
- [x] 5.3 Run migration upgrade/downgrade tests, focused backend security tests, `make test`, and the frontend test suite; record all results
