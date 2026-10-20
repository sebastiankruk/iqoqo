# activitypub-discovery-and-signatures Specification

## Purpose
WebFinger, NodeInfo 2.1, Actor JSON-LD endpoints, draft-cavage-12 HTTP Signatures, and SSRF-safe FederationClient.

## Requirements

### Requirement: Fediverse Discovery Standards

The system SHALL expose WebFinger and NodeInfo 2.1 endpoints returning standard JSON/JRD responses.

#### Scenario: WebFinger lookup returns JRD descriptor

- **WHEN** A GET request arrives at /.well-known/webfinger?resource=acct:user@domain for an opted-in user
- **THEN** Returns 200 OK with application/jrd+json pointing to the actor profile.

#### Scenario: WebFinger lookup preserves database session cache

- **WHEN** A WebFinger query is evaluated for an actor
- **THEN** The endpoint completes without calling session-wide invalidation or evicting unrelated ORM models.

### Requirement: HTTP Signature Verification & SSRF Defense

The system SHALL verify draft-cavage-12 signatures on incoming requests and prevent SSRF in outbound federation calls.

#### Scenario: Expired Date skew rejected

- **WHEN** An incoming signed request has Date header skewed by more than 300 seconds
- **THEN** Returns 401 Unauthorized.

#### Scenario: SSRF client blocks private IPs

- **WHEN** Outbound federation client attempts to fetch an actor on 127.0.0.1 or 192.168.0.0/16
- **THEN** The socket IP-pinning adapter blocks the connection.

### Requirement: Mandatory Signed Header Enforcement

The system SHALL enforce that all inbound HTTP signatures include `(request-target)`, `host`, `date`, and (when body is present) `digest` in the signed `headers="..."` list.

#### Scenario: Missing mandatory signed headers rejected

- **WHEN** An inbound request signs only `(request-target)` without `host` or `date`
- **THEN** Verification fails and returns 401 Unauthorized.

### Requirement: Horizontal Actor Impersonation Defense

The system SHALL verify that the actor URI declared in an ActivityPub payload strictly matches the authenticated signature key owner.

#### Scenario: Payload actor mismatch rejected

- **WHEN** A signed request from actor A submits an activity asserting actor B
- **THEN** Verification fails and returns 401 Unauthorized.

### Requirement: Inbound ActivityPub Inbox Protection

The system SHALL enforce rate limiting, payload size constraints, and recipient consent checks on inbox endpoints.

#### Scenario: Payload exceeds 100KB cap

- **WHEN** An inbound inbox POST exceeds 100KB in size
- **THEN** The request is rejected with 413 Payload Too Large.

#### Scenario: Follow delivery to non-consented user rejected

- **WHEN** An inbound Follow activity targets a local user who has not consented to federation
- **THEN** The request is rejected without creating follower records.

### Requirement: Authorized Outbound Federation Lookup

The system SHALL require authentication and rate limiting on outbound federation lookup endpoints to prevent SSRF amplification.

#### Scenario: Unauthenticated lookup rejected

- **WHEN** An unauthenticated client requests `GET /api/federation/lookup`
- **THEN** The endpoint returns 401 Unauthorized.

#### Scenario: Outbound lookup with port enforces HTTPS

- **WHEN** An outbound federation lookup targets a remote domain specifying a custom port (e.g. `domain.org:8443`)
- **THEN** The system constructs the query with scheme 'https' without downgrading to unencrypted HTTP.

### Requirement: CORS Discovery Boundary

The system SHALL restrict wildcard `Access-Control-Allow-Origin: *` headers exclusively to public read-only discovery routes (`/webfinger`, `/nodeinfo`, `/actor`), strictly prohibiting wildcard CORS on authenticated or state-changing routes.

#### Scenario: Authenticated federation route isolates CORS

- **WHEN** An authenticated route such as `/api/federation/consent` is accessed
- **THEN** It does not emit wildcard `Access-Control-Allow-Origin: *`.

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

### Requirement: Coalesced Key Rotation Re-Fetch and Tombstone Session Safety
`verify_request` in `app/core/http_signatures.py` SHALL enforce a minimum staleness cooldown before re-fetching a remote actor's public key on signature failure and SHALL persist newly verified rotated keys. `get_entity_tombstone` in `app/core/frbr_merge.py` SHALL detach (`expunge`) the `EntityAuditLog` instance from `db.session` before mutating `diff` in memory for multi-hop resolution.

#### Scenario: Rotated remote public key is persisted and cooldown prevents amplification

- **WHEN** an inbound signed request fails verification against a cached `FederationActor.public_key_pem`
- **THEN** `verify_request` only re-fetches the remote actor document if `last_fetched_at` is older than 60 seconds (or unset), and if the refreshed key verifies the signature, updates `public_key_pem` and `last_fetched_at` in the database
