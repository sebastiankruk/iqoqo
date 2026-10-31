## MODIFIED Requirements

### Requirement: Canonical Port-Preserving Peer Domain Normalization and Default Trust Clamping

All peer discovery, outbound actor caching, and inbound activity instance lookups SHALL normalize domains identically—stripping schemes, paths, and default ports (`:80`, `:443`) while preserving non-standard ports—and SHALL assign initial peer trust for newly registered or discovered instances to `untrusted` within the 3-state trust model (`trusted`, `untrusted`, `blocked`).

#### Scenario: Non-standard port is preserved uniformly across discovery and caching

- **WHEN** a peer operating at `https://library.example:8443` is discovered by an admin or cached during remote actor retrieval
- **THEN** the system stores and queries `domain = "library.example:8443"` consistently across discovery, actor caching, and inbound handlers

#### Scenario: Newly discovered peer honors clamped default trust

- **WHEN** a previously unseen peer domain is registered or discovered
- **THEN** the newly created `FederationInstance` record receives `trust_level = "untrusted"` (and any legacy `"pending"` value in database rows or API payloads is normalized to `"untrusted"`)

## ADDED Requirements

### Requirement: Three-Category Trust Gating Across Catalog Metadata, Friend Requests, and Collection/Loan Requests

The system SHALL enforce a unified 3-category trust model (`trusted`, `untrusted`, `blocked`) across catalog metadata synchronization, federated friend/follow requests, and federated collection/loan requests:
- **`trusted`**: Inbound catalog metadata auto-enriches empty fields with provenance; friend/follow requests and collection/loan requests are permitted, and inbound `Follow` requests may auto-accept if the target local user has enabled `auto_accept_follows`.
- **`untrusted`**: Inbound catalog metadata is queued as pending provenance candidates (`ProviderMergeDialog`) for custodian approval; friend/follow requests and collection/loan requests are permitted with mandatory manual user approval.
- **`blocked`**: All inbound and outbound catalog sync, friend/follow requests, and collection/loan requests are rejected (`HTTP 403`).

#### Scenario: Untrusted peer queues catalog metadata for review and requires manual follow approval

- **WHEN** a remote peer has `trust_level = "untrusted"` and sends either a catalog `Create`/`Update` activity or a `Follow` activity
- **THEN** `sync_manifestation` stores incoming bibliographic fields in `_pending_federation_sync` for custodian review without overwriting authoritative fields, and `handle_follow` records the follow request as `pending` for manual approval regardless of the user's `auto_accept_follows` toggle

#### Scenario: Blocked peer is rejected for outbound and inbound friend and loan requests

- **WHEN** a local user attempts to send a friend request or loan request to an actor on a `blocked` peer instance (or an actor on a `blocked` peer sends an inbound `Follow` or `Offer` activity)
- **THEN** the backend rejects the request with `PermissionError` / HTTP `403 Forbidden`
