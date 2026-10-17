# activitypub-discovery-and-signatures Specification

## Purpose
WebFinger, NodeInfo 2.1, Actor JSON-LD endpoints, draft-cavage-12 HTTP Signatures, and SSRF-safe FederationClient.

## Requirements

### Requirement: Fediverse Discovery Standards

The system SHALL expose WebFinger and NodeInfo 2.1 endpoints returning standard JSON/JRD responses.

#### Scenario: WebFinger lookup returns JRD descriptor

- **WHEN** A GET request arrives at /.well-known/webfinger?resource=acct:user@domain for an opted-in user
- **THEN** Returns 200 OK with application/jrd+json pointing to the actor profile.

### Requirement: HTTP Signature Verification & SSRF Defense

The system SHALL verify draft-cavage-12 signatures on incoming requests and prevent SSRF in outbound federation calls.

#### Scenario: Expired Date skew rejected

- **WHEN** An incoming signed request has Date header skewed by more than 300 seconds
- **THEN** Returns 401 Unauthorized.

#### Scenario: SSRF client blocks private IPs

- **WHEN** Outbound federation client attempts to fetch an actor on 127.0.0.1 or 192.168.0.0/16
- **THEN** The socket IP-pinning adapter blocks the connection.
