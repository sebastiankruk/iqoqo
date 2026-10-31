# activitypub-inbox-outbox Delta Specification

## ADDED Requirements

### Requirement: Robust WebFinger Resolution and Fallback
The WebFinger endpoint and outgoing handle resolution SHALL prevent SQL wildcard injection, prioritize exact public username matches, and ensure peer domain scoping is correctly appended when querying fallback remote instances.

#### Scenario: Username with wildcards does not execute arbitrary LIKE matching
- **WHEN** WebFinger lookup receives a resource with `%` or `_` wildcards
- **THEN** the system performs exact lowercase matching on `public_username` or `email` without substring expansion

#### Scenario: Fallback resolution appends remote instance domain
- **WHEN** an outgoing friend request handle does not contain a domain and falls back to querying registered instances
- **THEN** the system appends `@{domain}` to the WebFinger query and limits candidate instances to the top 5 recently seen peers

### Requirement: Strict Actor IRI Boundary Matching in Handlers
The inbound activity handlers for `Accept` and `Reject` SHALL verify that the target actor URI strictly ends with `/u/<user_uuid>` or matches the exact canonical Actor IRI, preventing partial substring collisions with arbitrary actor URLs.

#### Scenario: Actor URI with common prefix or substring is not falsely matched
- **WHEN** an inbound `Accept` or `Reject` activity contains an `actor_uri` containing a UUID substring but not ending with `/u/<user_uuid>`
- **THEN** the handler SHALL NOT match the target local user and SHALL reject the operation
