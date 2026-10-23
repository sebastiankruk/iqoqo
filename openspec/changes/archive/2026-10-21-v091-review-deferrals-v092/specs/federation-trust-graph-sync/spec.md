## ADDED Requirements

### Requirement: Multi-Tier FRBR Provenance Sync, Identifier Resolution, and Trust Audit Logging
`app/core/federation_sync.py`, `app/core/federation_discovery.py`, and `app/api/admin.py` SHALL support MusicBrainz (`mbid`) and BoardGameGeek (`bgg_id`) identifier resolution, auto-fill empty `Work` and `Expression` fields from `trusted` peers with `meta["_provenance"]` tracking, record `EntityAuditLog` entries on instance trust changes, and probe registered instances with bounded concurrency.

#### Scenario: Trusted peer enriches empty Work and Expression attributes via MusicBrainz or BGG identifier
- **WHEN** a `trusted` peer sends an `Update` activity matching a local item by `mbid` or `bgg_id` with a `description` or `language` that is currently empty on the local `Work` or `Expression`
- **THEN** `sync_manifestation` populates the empty `Work`/`Expression` field, records `meta["_provenance"][field] = f"federation:{domain}"`, and appends `prov:wasDerivedFrom`

#### Scenario: Admin trust level change is recorded in EntityAuditLog
- **WHEN** an administrator updates a `FederationInstance` trust level or deletes an instance via `/api/v1/admin/federation/instances/<id>`
- **THEN** the backend records an `EntityAuditLog` entry capturing the actor ID, previous trust level, and new trust level
