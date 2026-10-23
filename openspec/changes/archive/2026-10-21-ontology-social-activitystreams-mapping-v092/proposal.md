## Why
Establishes formal semantic mapping for social library concepts (followers, collections, custody transfers) into `iqoqo.ttl` and `iqoqo-shapes.ttl`.
## What Changes

- Map `UserCollection` -> `as:OrderedCollection`.
- Map `FederationFollower` / Friend -> `as:Follow` / `foaf:knows`.
- Map `UserWorkIntent` wishlist -> `schema:WantAction` / `as:Collection`.
- Map `ItemCustodyEvent` loan -> `crm:E10_Transfer_of_Custody` + `as:Offer` / `as:Accept`.
- Emit social triples in `public_rdf.py` and validate with `pyshacl` in CI.

## Capabilities

### New Capabilities
- `social-activitystreams-ontology`: OWL and SHACL ontology extensions mapping collections, friends, wishlists, and custody loans to ActivityStreams 2.0 and CIDOC CRM

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Ontology contracts in `docs/ontology/`, RDF exporter, and SHACL validation.
