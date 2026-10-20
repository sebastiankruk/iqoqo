# iri-immutability Specification

## Purpose

Immutable Canonical IRIs for ActivityPub Actors and FRBR Objects with tombstone generation on merges.

## Requirements

### Requirement: Immutable Canonical Actor IRI Resolution

The system SHALL generate Actor URIs using permanent, immutable user IDs that do not change when a user updates their username.

#### Scenario: Username change preserves canonical actor URI

- **WHEN** A user updates their account username in profile settings
- **THEN** The user's canonical Actor IRI remains invariant while WebFinger updates to resolve the new username.

### Requirement: FRBR Merge Tombstone and SameAs Redirection

The system SHALL emit owl:sameAs triples and ActivityStreams Move tombstones when an entity is merged into a canonical target.

#### Scenario: Deduplication merge produces tombstone and redirect

- **WHEN** A duplicate Manifestation or Work is merged via frbr_merge.py
- **THEN** The source IRI resolves to an ActivityStreams Move or RDF owl:sameAs pointer to the surviving target entity.

### Requirement: Chained Multi-Hop Tombstone Resolution
The system SHALL recursively resolve chained `owl:sameAs` and ActivityStreams `Move` tombstones so that querying any historical entity URI points directly to the ultimate surviving canonical entity.

#### Scenario: Chained merge resolves to final target

- **WHEN** Entity A is merged into Entity B, and Entity B is subsequently merged into Entity C
- **THEN** dereferencing Entity A returns a 301/410 redirect referencing Entity C.
