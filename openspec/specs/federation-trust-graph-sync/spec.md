# federation-trust-graph-sync Specification

## Purpose
Peer instance Trust Graph, health probes, provenance tracking, and Custodian Provider Merge queue integration.

## Requirements

### Requirement: Trust-Gated Metadata Reconciliation

The system SHALL auto-merge metadata only from trusted peers and queue pending peer updates for custodian review.

#### Scenario: Trusted peer updates empty field

- **WHEN** A trusted peer sends an Update activity for a Manifestation with empty page_count
- **THEN** Local field is updated and `meta['_provenance']['page_count']` records federation origin.

### Requirement: Local Hostname Verification and Input Sanitization in Federation Metadata Sync
`resolve_local_manifestation` and `sync_manifestation` in `app/core/federation_sync.py` SHALL verify that `/manifestation/<id>` URIs match the local instance hostname before querying by integer primary key, sanitize all inbound text strings with `bleach.clean`, and validate `http(s)` schemes on `cover_url`.

#### Scenario: Remote manifestation URI with foreign hostname does not collide with local primary key

- **WHEN** a remote peer sends a `Create` or `Update` activity whose object `id` is `https://remote.example/api/manifestations/1` and lacks matching ISBN/UPC/EAN identifiers
- **THEN** `resolve_local_manifestation` does not load local `Manifestation(id=1)` because `remote.example` does not match the local instance domain

#### Scenario: Malicious HTML and non-HTTP cover URLs are sanitized during sync

- **WHEN** a trusted or pending peer sends metadata containing HTML/script tags in `publisher` or `format` or a `javascript:`/`data:` URI in `cover_url`
- **THEN** `sync_manifestation` strips HTML tags via `bleach.clean(..., tags=[], strip=True)` and rejects non-`http(s)` `cover_url` values

### Requirement: Multi-Tier FRBR Provenance Sync, Identifier Resolution, and Trust Audit Logging
`app/core/federation_sync.py`, `app/core/federation_discovery.py`, and `app/api/admin.py` SHALL support MusicBrainz (`mbid`) and BoardGameGeek (`bgg_id`) identifier resolution, auto-fill empty `Work` and `Expression` fields from `trusted` peers with `meta["_provenance"]` tracking, record `EntityAuditLog` entries on instance creation, trust level changes, and deletions, and probe registered instances with bounded concurrency.

#### Scenario: Trusted peer enriches empty Work and Expression attributes via MusicBrainz or BGG identifier

- **WHEN** a `trusted` peer sends an `Update` activity matching a local item by `mbid` or `bgg_id` with a `description` or `language` that is currently empty on the local `Work` or `Expression`
- **THEN** `sync_manifestation` populates the empty `Work`/`Expression` field, records `meta["_provenance"][field] = f"federation:{domain}"`, and appends `prov:wasDerivedFrom`

#### Scenario: Admin trust level change is recorded in EntityAuditLog

- **WHEN** an administrator updates a `FederationInstance` trust level or deletes an instance via `/api/v1/admin/federation/instances/<id>`
- **THEN** the backend records an `EntityAuditLog` entry capturing the actor ID, previous trust level, and new trust level

#### Scenario: Admin instance addition is recorded in EntityAuditLog

- **WHEN** an administrator adds a peer instance via `POST /api/v1/admin/federation/instances`
- **THEN** the backend records an `EntityAuditLog` entry capturing the actor ID, domain, and initial trust state

### Requirement: Thread-Safe Periodic Instance Health Probing
The system SHALL execute only stateless HTTP NodeInfo/root discovery requests inside `ThreadPoolExecutor` worker threads in `probe_registered_instances`, and SHALL apply all SQLAlchemy ORM attribute mutations and `db.session.commit()` calls on the main calling thread.

#### Scenario: Concurrent health probe updates instance metadata safely

- **WHEN** `probe_registered_instances` probes multiple non-blocked `FederationInstance` records concurrently
- **THEN** worker threads perform HTTP requests without accessing `db.session`, and the main thread persists `last_seen_at`, `software_name`, `software_version`, and `shared_inbox_url` in a single thread-safe commit

### Requirement: Canonical Port-Preserving Peer Domain Normalization and Default Trust Clamping

All peer discovery, outbound actor caching, and inbound activity instance lookups SHALL normalize domains identically—stripping schemes, paths, and default ports (`:80`, `:443`) while preserving non-standard ports—and SHALL assign initial peer trust for newly registered or discovered instances to `untrusted` within the 3-state trust model (`trusted`, `untrusted`, `blocked`).

#### Scenario: Non-standard port is preserved uniformly across discovery and caching

- **WHEN** a peer operating at `https://library.example:8443` is discovered by an admin or cached during remote actor retrieval
- **THEN** the system stores and queries `domain = "library.example:8443"` consistently across discovery, actor caching, and inbound handlers

#### Scenario: Newly discovered peer honors clamped default trust

- **WHEN** a previously unseen peer domain is registered or discovered
- **THEN** the newly created `FederationInstance` record receives `trust_level = "untrusted"` (and any legacy `"pending"` value in database rows or API payloads is normalized to `"untrusted"`)

### Requirement: Cryptographic Verification of Peer Instance Key Fingerprints

During peer instance discovery and health probing, the system SHALL fetch the remote peer's advertised instance `Application` actor document (when available), cache its PEM public key, and compute the peer's `SHA256:...` fingerprint directly from the decoded public key DER bytes rather than trusting unverified self-asserted fingerprint strings.

#### Scenario: Peer discovery computes SHA-256 fingerprint from verified remote public key PEM

- **WHEN** an administrator adds or probes a remote peer that exposes an ActivityPub instance `Application` actor with a valid RSA `publicKeyPem`
- **THEN** the system caches the remote instance actor key and exposes the DER-computed `SHA256:...` `key_fingerprint` in the admin peer representation

### Requirement: Port-Preserving Metadata Sync, DER Key Fingerprinting, and Same-Origin Actor Discovery

The federation trust synchronization, cryptographic key fingerprinting, and peer discovery subsystems SHALL preserve non-standard ports when looking up `FederationInstance` trust in `reconcile_activity`, compute `SHA256:...` public key fingerprints from decoded ASN.1 DER `SubjectPublicKeyInfo` bytes, verify that NodeInfo `metadata.instance_actor` URLs share the exact normalized domain as the probed peer before fetching/caching actor keys, refresh cached instance actor keys cleanly during batch health probes without setting unmapped ORM attributes, exclude `.localdomain`/`.home.arpa`/`.lan` and bracketed IPv6 local addresses from the public directory, and bind the preview `peer-frontend` container port exclusively to `127.0.0.1`.

#### Scenario: Non-standard port on trusted hostname cannot spoof trusted metadata sync

- **WHEN** `trusted-peer.org` is `trusted` and an `Update` activity arrives from `https://trusted-peer.org:8443/u/rogue`
- **THEN** `reconcile_activity` queries `FederationInstance` using `trusted-peer.org:8443` rather than `trusted-peer.org` and refuses to auto-merge untrusted catalog metadata

#### Scenario: Public key fingerprint is invariant to PEM whitespace and line endings

- **WHEN** `compute_pem_fingerprint` evaluates the same RSA public key formatted with `\n` vs `\r\n` line endings or differing PEM armor whitespace (or receives invalid non-PEM text)
- **THEN** valid PEM inputs produce the identical DER-derived `SHA256:<hex>` digest and invalid/empty inputs return `"Not configured"`

#### Scenario: Cross-origin NodeInfo instance_actor URL is ignored during peer health probe

- **WHEN** probing `evil.example` returns a NodeInfo 2.1 document claiming `"metadata": {"instance_actor": "https://victim.example/api/federation/actor"}`
- **THEN** the health probe rejects the cross-origin `instance_actor` URL without fetching `victim.example` or polluting the local instance registry

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
