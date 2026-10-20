## ADDED Requirements

### Requirement: Public Key Cache Refresh on Signature Failure
When inbound HTTP signature verification fails against a cached public key, the system SHALL attempt to re-fetch the actor's remote JSON-LD document and retry verification once before failing, to handle remote actor key rotations seamlessly.

#### Scenario: Cached public key refreshed after verification failure
- **WHEN** an inbound signed ActivityPub request fails RSA signature verification using a cached actor key
- **THEN** the system re-fetches the remote Actor document, updates the cached public key, and re-verifies the request signature.

### Requirement: Strict WebFinger Domain Verification & Canonical URL
The WebFinger endpoint SHALL verify that the requested domain matches the host instance domain and link to canonical profile paths.

#### Scenario: Cross-domain WebFinger request rejected
- **WHEN** a WebFinger request specifies a handle with an external domain `acct:user@other-instance.org`
- **THEN** the system returns 404 Not Found.

#### Scenario: WebFinger profile links to canonical path
- **WHEN** a WebFinger request successfully resolves a local user
- **THEN** the profile link in the JRD descriptor uses the `/u/{username}` canonical URL.

### Requirement: Outbound Federation Exponential Backoff Retry
The outbound federation client SHALL retry transient network and HTTP 5xx failures using exponential backoff with connect/read timeouts of (10s, 30s).

#### Scenario: Outbound inbox delivery retried on 503
- **WHEN** delivering an activity to a remote inbox returns HTTP 503
- **THEN** the client retries delivery with exponential backoff up to 3 times before recording delivery failure.
