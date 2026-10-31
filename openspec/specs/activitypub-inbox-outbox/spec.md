# activitypub-inbox-outbox Specification

## Purpose
ActivityPub Actor/Shared Inboxes, read-only Outbox, async handlers, and Celery queue fan-out.

## Requirements

### Requirement: ActivityPub Inbound Message Handling

The system SHALL verify signatures and process ActivityPub activities asynchronously via Celery.

#### Scenario: Valid Follow activity queued

- **WHEN** A signed Follow activity arrives at the actor inbox
- **THEN** Returns 202 Accepted and queues Celery task.

### Requirement: ActivityPub Inbox Authorization, Payload Bounds, and Delivery Queue
The ActivityPub S2S Inbox (`POST /api/federation/inbox`, `POST /api/federation/actor/u/<user_uuid>/inbox`, `POST /api/federation/actor/<username>/inbox`), activity handlers, and Celery delivery pipeline SHALL enforce raw-byte payload bounds, target user federation consent, actor ownership on `Delete`, follow direction verification on `Accept`/`Reject`, `-Q celery,federation` worker consumption, HTTP 2xx delivery verification, and post-commit outbound fan-out with private-item filtering.

#### Scenario: Chunked request exceeding 100KB is rejected

- **WHEN** a remote client sends a POST request to `/api/federation/inbox` without a `Content-Length` header (or with `Transfer-Encoding: chunked`) whose body exceeds `FEDERATION_MAX_PAYLOAD_BYTES` (100KB)
- **THEN** the endpoint rejects the request with HTTP `413` before signature verification or JSON parsing

#### Scenario: Spoofed Delete or Accept(Follow) from non-owning remote actor is rejected

- **WHEN** remote actor `A` sends a `Delete` activity referencing actor `B`'s URI, or sends an `Accept(Follow)` for an inbound follow request where `A` is the follower awaiting local user approval
- **THEN** `handle_delete` and `handle_accept` reject the state mutation and preserve existing `FederationActor` and `FollowStatus.PENDING` records

#### Scenario: Outbound delivery checks HTTP status and hides private items

- **WHEN** a local user with `federated_collection=True` creates or deletes a public item (`is_hidden=False`), or when `deliver_activity` posts to a remote inbox returning HTTP 4xx/5xx
- **THEN** `_queue_and_deliver` commits `FederationActivity` rows before enqueuing onto the `federation` queue (skipping items where `is_hidden=True`), and `deliver_activity` marks non-2xx responses as `ActivityStatus.FAILED` while incrementing `federation_delivery_failures_total`

### Requirement: Opt-In Follow Auto-Accept and Canonical Peer Domain Resolution

The ActivityPub inbound `Follow` handler and actor resolution pipeline SHALL treat follow auto-acceptance as strictly opt-in per user (`FederationConsent.auto_accept_follows = False` by default), evaluate the target user's `FederationConsent.auto_accept_follows` preference together with the sender peer instance's `trust_level == "trusted"` at runtime, normalize remote peer domains with non-standard ports consistently, and assign initial peer trust for newly discovered instances to `"untrusted"`.

#### Scenario: Inbound Follow defaults to pending approval when auto-accept is unset or disabled

- **WHEN** a remote actor from a `trusted` or `untrusted` instance delivers a signed `Follow` activity and the target local user's `FederationConsent.auto_accept_follows` is unset or `false`
- **THEN** the system records the follow relationship as `pending`, emits an in-app follow-request notification to the target local user, and does NOT dispatch an automatic `Accept` activity

#### Scenario: Inbound Follow auto-accepts only when explicitly enabled in settings

- **WHEN** a local user explicitly sets `FederationConsent.auto_accept_follows` to `true` in their Profile Federation Settings and a remote actor from a `trusted` peer instance delivers a signed `Follow` activity to that consented user
- **THEN** the system records the follow relationship as `accepted` and dispatches a signed `Accept` activity to the follower's inbox

#### Scenario: Blocked peer on non-standard port cannot bypass blocklist via inbound activities

- **WHEN** an administrator has set trust level `blocked` on `malicious.example:8443` and an inbound signed activity arrives from `https://malicious.example:8443/u/attacker`
- **THEN** actor/instance resolution preserves `:8443` during domain normalization, matches the blocked `malicious.example:8443` instance record, and rejects the activity without creating a portless `malicious.example` record

### Requirement: Strict Opt-In Follow Auto-Accept, Follow State Preservation, and Port-Preserving Handler Enforcement

The ActivityPub inbound inbox and activity handlers (`Follow`, `Create`, `Update`, `Delete`, and `Announce`) SHALL normalize sender actor domains with non-standard ports preserved (`clean_instance_domain`), SHALL auto-accept inbound `Follow` requests ONLY when both the target user's `FederationConsent.auto_accept_follows` is `true` AND the sender's peer instance has trust level `trusted`, and SHALL preserve existing `accepted` or `rejected` follow states when duplicate `Follow` activities arrive.

#### Scenario: Trusted peer Follow remains pending when auto-accept is disabled

- **WHEN** the target local user's `FederationConsent.auto_accept_follows` is `false` and a remote actor on a `trusted` peer instance sends a signed `Follow` activity to that consented local user
- **THEN** the system records the follow relationship as `pending` for local user approval and does NOT auto-accept or grant `friends_only` visibility

#### Scenario: Untrusted peer Follow remains pending even when auto-accept is enabled

- **WHEN** the target local user's `FederationConsent.auto_accept_follows` is `true` and a remote actor on an `untrusted` peer instance sends a signed `Follow` activity
- **THEN** the system records the follow relationship as `pending` and does NOT auto-accept the untrusted follow request

#### Scenario: Duplicate Follow does not overwrite existing rejected or accepted relationship

- **WHEN** a remote actor whose previous follow request is already `rejected` (or already `accepted`) sends another `Follow` activity
- **THEN** a `rejected` relationship remains `rejected` without re-notifying, and an already `accepted` relationship remains `accepted` without being downgraded to `pending`

#### Scenario: Blocked or non-standard-port peer cannot bypass inbox or handler trust checks

- **WHEN** a peer registered as `blocked` on `evil.example:8443` sends any signed activity to `/inbox` or `/api/federation/inbox`, or an unprivileged service on `trusted.example:8443` sends `Create`/`Update`/`Delete`/`Announce` while `trusted.example` (port 443) is `trusted`
- **THEN** the inbox and handlers resolve `evil.example:8443` as `blocked` (`403`) and resolve `trusted.example:8443` independently of `trusted.example`

### Requirement: ActivityPub Follow Direction and Outbound Self-Response Prevention

The ActivityPub friendship and follow lifecycle SHALL distinguish between outbound and inbound pending Follow requests, and the system SHALL prohibit users from accepting or rejecting outbound follow requests they initiated themselves.

#### Scenario: User cannot respond to an outbound follow request they initiated

- **WHEN** an authenticated user attempts to call `POST /api/profile/friends/<friendship_id>/respond` with action `accept` or `reject` on a federated relationship where the local user is the initiator of the outbound `Follow` activity
- **THEN** the API rejects the request with HTTP `400 Bad Request` and an error indicating that outgoing requests cannot be accepted or rejected and must be cancelled instead

#### Scenario: User can cancel an outbound federated follow request

- **WHEN** an authenticated user calls `DELETE /api/profile/friends/<friendship_id>` for an outbound pending federated follow request
- **THEN** the system removes the pending follow relationship and returns HTTP `200 OK`

### Requirement: Resilient Inbox Task Submission Fallback and Flexible WebFinger Handle Resolution

The ActivityPub task dispatcher (`submit_task`) SHALL catch all broker and result-backend exceptions (including `RuntimeError` raised when Celery's Redis result backend is unreachable) so `receive_inbox` and `dispatch_activity` fall back cleanly to synchronous execution instead of returning HTTP `500`, and WebFinger / friend-request handle parsing SHALL split on the rightmost `@` while matching consented users by `public_username`, full `email`, or email local-part.

#### Scenario: Inbound Follow succeeds via synchronous fallback when Redis result backend is unreachable

- **WHEN** a remote instance delivers a signed `Follow` activity to `/api/federation/actor/u/<user_uuid>/inbox` and the receiving instance's Celery Redis broker or result backend raises `RuntimeError` or `KombuError`
- **THEN** `submit_task` catches the exception, logs a warning, and returns `None` so `receive_inbox` executes `process_inbound_activity` synchronously, creates the `FederationFollower` row, emits the in-app notification, and returns HTTP `202 Accepted`

#### Scenario: Friend request and WebFinger resolve email-based federated handles

- **WHEN** a user submits a friend request for `peer-admin@iqoqo.cc@peer.iqoqo.cc`, `peer-admin@peer.iqoqo.cc`, or `peer-admin@iqoqo.cc` where the target user on `peer.iqoqo.cc` has `email = "peer-admin@iqoqo.cc"`, `public_username = "peeradmin"`, and `federated_profile = True`
- **THEN** handle parsing splits on the rightmost `@` (or falls back across registered non-blocked peer instances when the domain is an email domain not matching a local user), WebFinger matches the consented user by `public_username`, full `email`, or email local-part (`peer-admin`), and the outbound `Follow` activity is delivered to `peer.iqoqo.cc`

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
