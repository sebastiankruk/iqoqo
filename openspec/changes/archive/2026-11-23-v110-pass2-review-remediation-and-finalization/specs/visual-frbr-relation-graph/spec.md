## MODIFIED Requirements

### Requirement: Bounded and Visibility-Safe Catalog Relation Graph Endpoint
The backend SHALL expose `GET /api/catalog/graph` accepting `entity_type` (`work`, `expression`, `manifestation`, `item`), `entity_id`, and `depth` (`1` or `2`, clamped to `2`), returning deterministic `nodes` and `edges` capped at `150` nodes, strictly enforcing three-tier `Item` visibility privacy (`public`, `friends_only`, `private`), and bounding/batching per-hop SQL queries (including expression manifestation expansions and item container parent lookups).

#### Scenario: Querying a 1-hop or 2-hop FRBR neighborhood around a Work

- **GIVEN** a `Work` with `Expression`s, `Manifestation`s, an `Item` (`private` owned by User A and `public` owned by User B), a `Series`, a `WorkExpansionLink`, and accepted `SemanticLink`s
- **WHEN** an unauthenticated visitor or User C requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=2`
- **THEN** the response MUST return HTTP `200` with the FRBR tree, series, expansion, and LOD nodes/edges plus User B's `public` `Item`, and MUST omit User A's `private` `Item`.
- **WHEN** User A requests the same endpoint
- **THEN** User A's `private` `Item` MUST be included alongside User B's `public` `Item`.

#### Scenario: Bounding depth and total nodes on dense entities

- **GIVEN** an entity connected to more than 150 nodes (such as a serial `Expression` with hundreds of `Manifestation` issues or an `Item` aggregated into container `Work`s) or queried with `depth=99`
- **WHEN** `GET /api/catalog/graph` executes
- **THEN** `depth` MUST clamp to `2`, `Expression` manifestation queries MUST be bounded by the `150`-node graph cap, container `Work` lookups MUST be batched, `nodes` MUST NOT exceed `150` entries, and `meta.truncated` MUST indicate when truncation occurred.
