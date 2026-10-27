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

The ActivityPub inbound `Follow` handler and actor resolution pipeline SHALL treat follow auto-acceptance as strictly opt-in (`false` by default), evaluate dynamic administrator configuration at runtime, normalize remote peer domains with non-standard ports consistently, and clamp default peer trust to non-privileged levels (`untrusted` or `pending`).

#### Scenario: Inbound Follow defaults to pending approval when auto-accept is unset or disabled

- **WHEN** a remote actor from an `untrusted` or `pending` instance delivers a signed `Follow` activity and `FEDERATION_AUTO_ACCEPT_FOLLOWS` is unset or `false`
- **THEN** the system records the follow relationship as `pending`, emits an in-app follow-request notification to the target local user, and does NOT dispatch an automatic `Accept` activity

#### Scenario: Inbound Follow auto-accepts only when explicitly enabled in settings

- **WHEN** an administrator explicitly sets `FEDERATION_AUTO_ACCEPT_FOLLOWS` to `true` and a remote actor from a non-blocked instance delivers a signed `Follow` activity to a consented user
- **THEN** the system records the follow relationship as `accepted` and dispatches a signed `Accept` activity to the follower's inbox

#### Scenario: Blocked peer on non-standard port cannot bypass blocklist via inbound activities

- **WHEN** an administrator has set trust level `blocked` on `malicious.example:8443` and an inbound signed activity arrives from `https://malicious.example:8443/u/attacker`
- **THEN** actor/instance resolution preserves `:8443` during domain normalization, matches the blocked `malicious.example:8443` instance record, and rejects the activity without creating a portless `malicious.example` record

### Requirement: Strict Opt-In Follow Auto-Accept, Follow State Preservation, and Port-Preserving Handler Enforcement

The ActivityPub inbound inbox and activity handlers (`Follow`, `Create`, `Update`, `Delete`, and `Announce`) SHALL normalize sender actor domains with non-standard ports preserved (`clean_instance_domain`), SHALL auto-accept inbound `Follow` requests ONLY when both `FEDERATION_AUTO_ACCEPT_FOLLOWS` is `true` AND the sender's peer instance has trust level `trusted`, and SHALL preserve existing `accepted` or `rejected` follow states when duplicate `Follow` activities arrive.

#### Scenario: Trusted peer Follow remains pending when auto-accept is disabled

- **WHEN** `FEDERATION_AUTO_ACCEPT_FOLLOWS` is `false` and a remote actor on a `trusted` peer instance sends a signed `Follow` activity to a consented local user
- **THEN** the system records the follow relationship as `pending` for local user approval and does NOT auto-accept or grant `friends_only` visibility

#### Scenario: Untrusted peer Follow remains pending even when auto-accept is enabled

- **WHEN** `FEDERATION_AUTO_ACCEPT_FOLLOWS` is `true` and a remote actor on an `untrusted` or `pending` peer instance sends a signed `Follow` activity
- **THEN** the system records the follow relationship as `pending` and does NOT auto-accept the untrusted follow request

#### Scenario: Duplicate Follow does not overwrite existing rejected or accepted relationship

- **WHEN** a remote actor whose previous follow request is already `rejected` (or already `accepted`) sends another `Follow` activity
- **THEN** a `rejected` relationship remains `rejected` without re-notifying, and an already `accepted` relationship remains `accepted` without being downgraded to `pending`

#### Scenario: Blocked or non-standard-port peer cannot bypass inbox or handler trust checks

- **WHEN** a peer registered as `blocked` on `evil.example:8443` sends any signed activity to `/inbox` or `/api/federation/inbox`, or an unprivileged service on `trusted.example:8443` sends `Create`/`Update`/`Delete`/`Announce` while `trusted.example` (port 443) is `trusted`
- **THEN** the inbox and handlers resolve `evil.example:8443` as `blocked` (`403`) and resolve `trusted.example:8443` independently of `trusted.example`
