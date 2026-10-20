## ADDED Requirements

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
