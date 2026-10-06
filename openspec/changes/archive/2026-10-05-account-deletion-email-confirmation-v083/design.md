## Context

See `proposal.md` for motivation and scope. The current account deletion endpoint immediately deletes the authenticated user, relying on database cascades for associated data. The user record has an email address but no persisted email-verification state, local registration does not verify email, and the authentication decorator currently validates JWT signature/expiry and a per-token blocklist without checking whether the account still exists. There is no existing outbound email service in the application code.

Email confirmation is mailbox-ownership confirmation, not proof of fresh password or federated authentication. The flow must therefore require both the email token and an authenticated session for the same account at the final confirmation step.

## Goals / Non-Goals

**Goals:**
- Establish trustworthy email verification for local and federated accounts.
- Make account deletion an explicit two-step request/confirmation flow that is safe around email scanners and repeat requests.
- Guarantee that successful deletion invalidates all previously issued account credentials.
- Support the email flow in self-hosted deployments with explicit, documented delivery configuration.

**Non-Goals:**
- Treat email possession as equivalent to strong recent authentication or a second authentication factor.
- Add an account-deletion grace period or a weaker manual bypass for accounts without a verified email.
- Redesign unrelated account deletion data-retention semantics; preserve the existing delete/cascade behavior.

## Decisions

### Decision 1: Persist verified-email state and invalidate it on change

Add a verification timestamp/state for the account email. Local email addresses become verified only after the owner completes a separate purpose-bound email verification flow. Federated addresses may be marked verified only when the validated OIDC identity response asserts a verified email claim. Any email change clears verification and invalidates outstanding verification and deletion requests. This avoids treating an arbitrary address stored on a user row as proof of mailbox control.

**Alternative considered:** Send a deletion link to any stored email address and treat link access as sufficient. Rejected because unverified account data may contain an address controlled by someone other than the account owner.

### Decision 2: Use a configured transactional email service

Add a small mail-delivery boundary with explicit SMTP/TLS configuration suitable for self-hosted deployments; do not assume a provider or credentials are available by default. Local tests use a capture/fake transport. Production deletion and email verification flows fail safely with a clear service-configuration error when outbound email is unavailable; they do not silently fall back to password-only deletion or reveal whether an address/account exists.

**Alternative considered:** A cloud-provider-specific mail SDK. Rejected to avoid locking self-hosted installations to one vendor.

### Decision 3: Purpose-bound, hashed, expiring single-use tokens

Generate at least 32 bytes of cryptographically secure random token material. Persist only a one-way digest plus user ID, purpose, creation/expiry timestamps, and consumption state. Use separate purposes for email verification and deletion confirmation. Set deletion confirmation expiry to 30 minutes. A resend invalidates earlier outstanding tokens for that account and purpose. Apply issuance and verification-attempt limits by account and source; never log tokens or complete URLs.

**Alternative considered:** Store plaintext or reusable confirmation codes. Rejected because database/log exposure or replay would enable account deletion.

### Decision 4: Require the same authenticated account, not the exact browser session

The request record is bound to its account. Final confirmation requires a currently authenticated session for that same account and CSRF protection for cookie-based authentication. Requiring the identical browser session would make email links opened on a second device unnecessarily unusable; accepting a token without re-authentication would make the email URL alone a bearer credential capable of deleting the account.

### Decision 5: Keep email-link GET non-destructive

GET requests only display or route to a confirmation page. The final operation is a deliberate POST that verifies the user session, CSRF proof where applicable, token purpose, expiry, and account binding. The page must avoid third-party resources, apply a `no-referrer` policy, and avoid exposing the token in logs. Confirmation must remain safe under repeated and concurrent GET requests.

**Alternative considered:** Delete directly on link GET. Rejected because mail-security scanners and browser prefetching routinely follow links automatically.

### Decision 6: Atomically delete and invalidate credentials

Consume the token and apply the existing account deletion operation in one database transaction. The auth boundary must reject credentials for a missing or inactive user, so a deleted account's previously issued JWTs cannot remain usable until expiration. A completion notification should be queued/delivered after commit; notification failure must not restore the deleted account. Use a retryable notification mechanism where available and retain only the minimum delivery data required.

**Alternative considered:** Rely only on the existing per-JWT blocklist. Rejected because it does not enumerate or revoke every outstanding stateless JWT issued to an account.

### Decision 7: Immediate deletion after explicit confirmation

The account and associated data are deleted according to current cascade semantics after the final confirmation. No post-confirmation grace period is provided. The UI and email must clearly state that the confirmed action is permanent; a request can be abandoned before confirmation without any account data being removed.

### Decision 8: Confirmation screens are frontend routes, not backend responses

The emailed links point at application routes (`/account/verify`, `/account/delete`) rendered by the Next.js frontend, and the backend exposes JSON for their state and mutations. Response headers that protect a token-bearing page (`Referrer-Policy: no-referrer`, `X-Frame-Options`, `Cache-Control: no-store`, `X-Robots-Tag`) move with them into `next.config.ts`.

**Alternative considered:** Server-rendered confirmation pages from the backend, with their own stylesheet. Rejected on security grounds rather than aesthetic ones: a styleless, unbranded page arriving by email is what a phishing page looks like, so it trains recipients to distrust the genuine article. It was built this way first and had to be redone. The boundary is now a project rule ("Flask Is API-Only") enforced by `tests/test_api_only_rule.py`.

**Consequence:** the browser sends the token in a JSON POST body rather than a query string, so the backend must read the token from args, form, *and* JSON. Getting this wrong was silent: the state GET reported the link usable and the next POST refused the same token as spent.

## Risks / Trade-offs

- **[Risk] Mailbox compromise enables confirmation** → Require a currently authenticated session for the same account as well as possession of the email token; accurately describe email as mailbox ownership, not fresh authentication.
- **[Risk] Email misconfiguration blocks verification and deletion** → Fail safely, explain the configuration problem without account enumeration, and document required deployment settings and a local test transport.
- **[Risk] Link scanners or concurrent requests trigger unintended actions** → Keep GET side-effect free and make final POST atomic, CSRF-protected where applicable, and idempotent against token replay.
- **[Risk] Stateless JWTs remain valid after account deletion** → Make protected authentication reject missing/inactive users and test existing access and cookie credentials after deletion.
- **[Risk] Email delivery fails after the irreversible database change** → Commit deletion independently of delivery, queue/retry completion notification, and do not retain the deleted user account to retry mail.
- **[Risk] Verification state and address changes become inconsistent** → Clear the verified timestamp and pending tokens whenever the email changes; enforce this behavior in the service/model and tests.

## Migration Plan

1. Add the email-verification state and deletion/email-verification token persistence with reversible migrations; existing addresses begin unverified unless their verification can be established from trusted OIDC data.
2. Configure the outbound mail transport and templates, then deploy the backend and frontend flows. Document required mail settings for self-hosted deployments.
3. Keep account deletion unavailable until the user has a verified address and mail delivery is operational; do not preserve the old immediate-delete endpoint as a bypass.
4. On downgrade, remove new token records and verification columns only after ensuring no active verification or deletion flow depends on them. Account data deletion itself is irreversible and has no rollback.

## Open Questions

None. The expiry, verification policy, session binding, no-grace-period behavior, and missing-email behavior are defined above.
