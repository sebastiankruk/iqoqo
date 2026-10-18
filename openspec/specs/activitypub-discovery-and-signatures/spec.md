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
