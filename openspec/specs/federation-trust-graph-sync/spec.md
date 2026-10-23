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
`app/core/federation_sync.py`, `app/core/federation_discovery.py`, and `app/api/admin.py` SHALL support MusicBrainz (`mbid`) and BoardGameGeek (`bgg_id`) identifier resolution, auto-fill empty `Work` and `Expression` fields from `trusted` peers with `meta["_provenance"]` tracking, record `EntityAuditLog` entries on instance trust changes, and probe registered instances with bounded concurrency.

#### Scenario: Trusted peer enriches empty Work and Expression attributes via MusicBrainz or BGG identifier

- **WHEN** a `trusted` peer sends an `Update` activity matching a local item by `mbid` or `bgg_id` with a `description` or `language` that is currently empty on the local `Work` or `Expression`
- **THEN** `sync_manifestation` populates the empty `Work`/`Expression` field, records `meta["_provenance"][field] = f"federation:{domain}"`, and appends `prov:wasDerivedFrom`

#### Scenario: Admin trust level change is recorded in EntityAuditLog

- **WHEN** an administrator updates a `FederationInstance` trust level or deletes an instance via `/api/v1/admin/federation/instances/<id>`
- **THEN** the backend records an `EntityAuditLog` entry capturing the actor ID, previous trust level, and new trust level

### Requirement: Thread-Safe Periodic Instance Health Probing
The system SHALL execute only stateless HTTP NodeInfo/root discovery requests inside `ThreadPoolExecutor` worker threads in `probe_registered_instances`, and SHALL apply all SQLAlchemy ORM attribute mutations and `db.session.commit()` calls on the main calling thread.

#### Scenario: Concurrent health probe updates instance metadata safely

- **WHEN** `probe_registered_instances` probes multiple non-blocked `FederationInstance` records concurrently
- **THEN** worker threads perform HTTP requests without accessing `db.session`, and the main thread persists `last_seen_at`, `software_name`, `software_version`, and `shared_inbox_url` in a single thread-safe commit
