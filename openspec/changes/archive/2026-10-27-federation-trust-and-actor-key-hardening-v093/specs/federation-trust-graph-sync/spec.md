## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Canonical Port-Preserving Peer Domain Normalization and Default Trust Clamping

All peer discovery, outbound actor caching, and inbound activity instance lookups SHALL normalize domains identically—stripping schemes, paths, and default ports (`:80`, `:443`) while preserving non-standard ports—and SHALL clamp initial peer trust for newly registered instances to `untrusted` or `pending`.

#### Scenario: Non-standard port is preserved uniformly across discovery and caching

- **WHEN** a peer operating at `https://library.example:8443` is discovered by an admin or cached during remote actor retrieval
- **THEN** the system stores and queries `domain = "library.example:8443"` consistently across discovery, actor caching, and inbound handlers

#### Scenario: Newly discovered peer honors clamped default trust

- **WHEN** a previously unseen peer domain is discovered while `FEDERATION_DEFAULT_TRUST` is set to `"pending"` (or if corrupted to `"trusted"`)
- **THEN** the newly created peer record receives trust level `"pending"` (or falls back to `"untrusted"` when the configured value is not in `{"untrusted", "pending"}`)

### Requirement: Cryptographic Verification of Peer Instance Key Fingerprints

During peer instance discovery and health probing, the system SHALL fetch the remote peer's advertised instance `Application` actor document (when available), cache its PEM public key, and compute the peer's `SHA256:...` fingerprint directly from the decoded public key DER bytes rather than trusting unverified self-asserted fingerprint strings.

#### Scenario: Peer discovery computes SHA-256 fingerprint from verified remote public key PEM

- **WHEN** an administrator adds or probes a remote peer that exposes an ActivityPub instance `Application` actor with a valid RSA `publicKeyPem`
- **THEN** the system caches the remote instance actor key and exposes the DER-computed `SHA256:...` `key_fingerprint` in the admin peer representation
