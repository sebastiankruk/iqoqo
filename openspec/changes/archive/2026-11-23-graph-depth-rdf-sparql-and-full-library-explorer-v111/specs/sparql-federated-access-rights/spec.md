## MODIFIED Requirements

### Requirement: SQL-Pushed SPARQL Friend Scoping and Three-Tier Visibility Enforcement
The system SHALL resolve accepted local friend UUIDs via `get_friend_user_ids(user.id)` in `_get_sparql_items`, push owner, friend (`visibility in ('public', 'friends_only', 'shared')`), `FederationConsent.federated_collection` exclusion for non-owner/non-friend public rows, and public visibility predicates into the SQL `WHERE` clause prior to `LIMIT`, and preserve accepted friends' `friends_only` items during `build_graph` (both when pre-filtered `items` are supplied and when `build_graph` queries the database directly) without executing per-item `is_friend_of` or `is_item_publicly_visible` N+1 SQL queries.

#### Scenario: Accepted friend queries a friend's friends_only item via SPARQL

- **WHEN** an authenticated user executes a `SELECT` query on `/sparql` matching an item owned by an accepted local friend with `visibility="friends_only"`
- **THEN** the item's triples are included in the SPARQL snapshot and returned in the query results, while the friend's `private` items remain excluded

#### Scenario: Building a SPARQL snapshot or graph projection without N+1 visibility queries

- **WHEN** `build_graph` constructs an RDF graph for up to `MAX_GRAPH_ITEMS` items (whether invoked from `/api/sparql` or from an RDF/SPARQL-backed graph projection)
- **THEN** accepted friend IDs and `FederationConsent` exclusions MUST be resolved in bulk/SQL prior to triple emission with zero per-item friendship or consent SQL queries, and `friends_only` / `FederationConsent.federated_collection == False` items MUST obey identical visibility rules as `_get_sparql_items`.

## ADDED Requirements

### Requirement: RDF and Graph Projection Relation Parity and Read-Only Federation Compatibility
Any RDF snapshot or SPARQL projection supporting catalog graph exploration SHALL emit complete FRBR/FRBRoo and semantic link coverage matching the catalog relation graph (`Work`, `Expression`, `Manifestation`, `Item`, `Contributor`, `WorkPart`, `WorkSeriesMembership`, `WorkExpansionLink`, `ContainerAggregation`, stable map attachment identifiers, and `SemanticLink` triples for `work`, `expression`, and `manifestation` strictly filtered to `status == "accepted"`), while remaining permitted for read-only exploration under `FEDERATION_HEAD_MODE=true`.

#### Scenario: Emitting expansion, container aggregation, and accepted expression semantic links in RDF snapshots

- **WHEN** an RDF collection snapshot is constructed from entities containing a `WorkExpansionLink`, a `ContainerAggregation`, an accepted `Expression`-scoped `SemanticLink`, and a pending `SemanticLink`
- **THEN** the resulting RDF graph MUST include triples for the `WorkExpansionLink`, `ContainerAggregation`, and accepted `Expression` `SemanticLink`, and MUST omit the pending `SemanticLink`.

#### Scenario: Serving read-only SPARQL and RDF graph queries in FEDERATION_HEAD_MODE

- **GIVEN** an instance running with `FEDERATION_HEAD_MODE=true`
- **WHEN** an authorized client issues read-only SPARQL `SELECT`/`ASK`/`CONSTRUCT`/`DESCRIBE` queries or catalog graph explorer requests
- **THEN** read-only graph and SPARQL queries MUST succeed without triggering the physical `Item` write `403` guard, while still enforcing `Item` three-tier visibility and `FederationConsent`.
