# account-deletion-confirmation Specification

## Purpose

Provides a safe, auditable account-deletion process that confirms mailbox
ownership and account-session control before permanently deleting a user's
account and associated data.

## Requirements

### Requirement: Verified Account Email

The system SHALL maintain a trustworthy verification state for the email address
associated with each account. Locally supplied email addresses SHALL be verified
through a confirmation sent to that address; federated email addresses SHALL be
treated as verified only when the validated identity response asserts that the
email is verified. Changing an account email SHALL clear its verified state until
the new address is verified.

#### Scenario: Local account verifies its email address

- **WHEN** a user follows a valid email-verification confirmation for the address
  currently stored on their account
- **THEN** the system marks that address as verified and rejects reuse of the
  verification token

#### Scenario: Federated identity provides a verified email

- **WHEN** a user signs in through a validated OIDC identity response that
  asserts the account email is verified
- **THEN** the system may mark the matching email address as verified for that
  account

#### Scenario: User changes their account email

- **WHEN** a user's account email address changes
- **THEN** the old verification state and any pending verification or
  deletion-confirmation tokens are invalidated until the new address is verified

### Requirement: Account Deletion Request

The system SHALL require an authenticated account owner to explicitly initiate
account deletion and SHALL send a deletion-confirmation message only to the
verified email address already associated with that account. Initiating a request
SHALL NOT delete or anonymize the account. Responses SHALL not disclose account or
email existence to unauthenticated callers, and request issuance SHALL be
rate-limited.

#### Scenario: Authenticated user initiates deletion

- **WHEN** an authenticated user with a verified email requests account deletion
- **THEN** the system creates a pending deletion request, sends a confirmation
  message to the account's verified email, and leaves the account and its data
  unchanged

#### Scenario: User without a verified email requests deletion

- **WHEN** an authenticated user attempts to initiate deletion without a verified
  email address
- **THEN** the system does not create a deletion request or send a deletion link
  and directs the user to verify or add an email address first

#### Scenario: Unauthenticated caller attempts deletion initiation

- **WHEN** a caller without a valid account session attempts to initiate deletion
- **THEN** the system rejects the request without disclosing whether an account or
  email address exists

#### Scenario: Initiation rate limit is exceeded

- **WHEN** a user or source exceeds the configured deletion-request or resend
  limit
- **THEN** the system refuses additional messages for the limit window without
  creating additional active confirmation requests

#### Scenario: User receives a deletion request notification

- **WHEN** the system creates a pending deletion request
- **THEN** the email clearly states that deletion has not yet occurred, explains
  how to confirm, and tells the recipient to ignore the message if they did not
  request deletion

### Requirement: Secure Deletion Confirmation Token

Each deletion-confirmation token SHALL be cryptographically random, bound to one
account and the deletion-confirmation purpose, stored only as a secure digest,
expire after 30 minutes, and be usable at most once. Issuing a replacement request
SHALL invalidate earlier pending deletion tokens. Tokens and token-bearing URLs
SHALL NOT be written to application logs or referrer headers.

#### Scenario: Confirmation token is persisted securely

- **WHEN** the system creates a deletion-confirmation request
- **THEN** it stores only a secure digest bound to the account and deletion
  purpose, with an expiry no later than 30 minutes after issuance

#### Scenario: Replacement request invalidates the prior token

- **WHEN** a new deletion-confirmation email is issued for the same account
- **THEN** all earlier pending deletion-confirmation tokens for that account
  become unusable

#### Scenario: Expired, altered, or wrong-purpose token is presented

- **WHEN** confirmation is attempted with an expired, altered, or token issued
  for another purpose
- **THEN** the system rejects the attempt without changing the account or
  consuming a valid unrelated token

#### Scenario: Confirmation token is replayed

- **WHEN** a token that has already completed or is superseded is submitted again
- **THEN** the system rejects the replay and performs no additional action

### Requirement: Scanner-Safe Explicit Confirmation

Opening an email confirmation URL SHALL NOT delete the account, consume the token,
or otherwise mutate state. Final confirmation SHALL require an explicit
state-changing request by an authenticated session for the same account, with
CSRF protection when cookie authentication is used. The confirmation page SHALL be
rendered by the application frontend, so that it carries the product's own
navigation, layout and design system rather than a separate hand-written surface,
and it SHALL clearly explain that account deletion is permanent.

#### Scenario: Email client or scanner opens the link

- **WHEN** a mail scanner, preview service, or browser prefetcher requests the
  confirmation URL with GET
- **THEN** the system renders a frontend confirmation route, or redirects to one,
  without consuming the token or changing account state

#### Scenario: Correct account confirms deletion

- **WHEN** the account owner authenticates as the account associated with the
  pending request and explicitly submits a valid confirmation with required CSRF
  protection
- **THEN** the system proceeds with deletion exactly once

#### Scenario: Different account attempts to confirm

- **WHEN** a valid email token is submitted from an authenticated session
  belonging to a different account
- **THEN** the system refuses confirmation and leaves both accounts and the
  pending request unchanged

#### Scenario: Confirmation lacks valid CSRF proof

- **WHEN** a cookie-authenticated confirmation POST lacks valid CSRF proof
- **THEN** the system rejects the request without consuming the token or deleting
  the account

### Requirement: Confirmed Deletion and Credential Revocation

After a valid explicit confirmation, the system SHALL atomically consume the
deletion token and apply the established account-deletion semantics. It SHALL make
every previously issued credential for the deleted account unusable before
returning success, and SHALL NOT introduce a post-confirmation grace period.

#### Scenario: Valid confirmation completes account deletion

- **WHEN** a valid, unexpired token is confirmed by an authenticated session for
  the same account
- **THEN** the system consumes the token and permanently deletes or anonymizes
  the account and associated data according to the established account-deletion
  behavior, without a grace period

#### Scenario: Previously issued credentials are reused after deletion

- **WHEN** a caller attempts to use a previously issued JWT or session credential
  after account deletion succeeds
- **THEN** authentication is rejected and no protected account operation succeeds

#### Scenario: Deletion processing fails

- **WHEN** an error prevents the account-deletion transaction from completing
- **THEN** the account is not partially deleted and the confirmation request
  remains in a safe, retryable or invalidated state without permitting duplicate
  deletion effects

### Requirement: Deletion Notifications

The system SHALL notify the verified account email when deletion is requested and
after deletion completes. The request notification SHALL make clear that no
deletion occurs until the owner confirms. Notifications SHALL NOT contain
confirmation tokens or unnecessary sensitive account data.

#### Scenario: Deletion completes

- **WHEN** account deletion succeeds
- **THEN** the system queues or sends a completion notice to the verified email
  address without including the confirmation token

#### Scenario: Deletion notification delivery is temporarily unavailable

- **WHEN** the email service is temporarily unavailable after a deletion event is
  recorded
- **THEN** the account-deletion result remains consistent and the notification is
  retried or reported as a delivery failure without restoring the deleted account
