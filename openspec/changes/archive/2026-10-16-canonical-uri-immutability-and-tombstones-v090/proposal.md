## Why
ActivityPub federation and Linked Open Data require permanent, dereferenceable IRIs. If Actor IDs change when display usernames change, or if merged FRBR objects disappear without trace, remote Fediverse instances break link resolution and cache coherence.
## What Changes

- Lock canonical Actor URIs in `app/core/iri.py` to immutable user identifiers (UUIDs/permanent IDs) decoupled from mutable username display changes.
- Maintain WebFinger dynamic mapping from `acct:username@domain` to immutable canonical Actor URI.
- Emit RDF `owl:sameAs` triples and ActivityStreams `Move` / `Tombstone` activities when duplicate FRBR entities are merged via `app/core/frbr_merge.py`.
- Add IRI immutability verification test suite in `tests/test_iri_immutability.py`.

## Capabilities

### New Capabilities
- `iri-immutability`: Immutable Canonical IRIs for ActivityPub Actors and FRBR Objects with tombstone generation on merges

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Updates `app/core/iri.py`, `app/core/frbr_merge.py`, `app/api/public_rdf.py`, and test suites.
