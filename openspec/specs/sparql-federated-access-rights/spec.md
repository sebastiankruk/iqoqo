# sparql-federated-access-rights Specification

## Purpose
Enforce privacy boundaries across SPARQL runner snapshots and public RDF exports, and record Fuseki evaluation ADR.

## Requirements

### Requirement: SPARQL Snapshot Privacy Scoping

The system SHALL exclude non-consented users and private items from unauthenticated SPARQL execution snapshots.

#### Scenario: Private item excluded from public SPARQL

- **WHEN** A public SPARQL query searches for all items
- **THEN** Items with is_public=False are omitted from the snapshot graph.

### Requirement: SQL-Pushed SPARQL Friend Scoping and Three-Tier Visibility Enforcement

The system SHALL resolve accepted local friend UUIDs via `get_friend_user_ids(user.id)` in `_get_sparql_items`, push owner, friend (`visibility in ('public', 'friends_only', 'shared')`), `FederationConsent.federated_collection` exclusion strictly for non-owner/non-friend public rows (exempting `friend_ids` from `opted_out_ids` via a shared SQL visibility predicate helper across `SparqlService` and `GraphService`), and public visibility predicates into the SQL `WHERE` clause prior to `LIMIT`, and preserve accepted friends' `public`, `friends_only`, and `shared` items during `build_graph` (both when pre-filtered `items` are supplied and when `build_graph` queries the database directly) without executing per-item `is_friend_of` or `is_item_publicly_visible` N+1 SQL queries.

#### Scenario: Accepted friend queries a friend's friends_only item via SPARQL

- **WHEN** an authenticated user executes a `SELECT` query on `/sparql` matching an item owned by an accepted local friend with `visibility="friends_only"`
- **THEN** the item's triples are included in the SPARQL snapshot and returned in the query results, while the friend's `private` items remain excluded

#### Scenario: Accepted friend queries a friend's public item when the friend has opted out of public federation

- **GIVEN** User B has `FederationConsent.federated_collection == False` and owns both a `public` item and a `friends_only` item
- **WHEN** User A (an accepted local friend of User B) executes a `SELECT` query on `/sparql`
- **THEN** both User B's `public` item and `friends_only` item MUST be included in the SPARQL snapshot, whereas an unauthenticated caller or non-friend MUST see neither item.

#### Scenario: Building a SPARQL snapshot or graph projection without N+1 visibility queries

- **WHEN** `build_graph` constructs an RDF graph for up to `MAX_GRAPH_ITEMS` items (whether invoked from `/api/sparql` or from an RDF/SPARQL-backed graph projection)
- **THEN** accepted friend IDs and `FederationConsent` exclusions MUST be resolved in bulk/SQL prior to triple emission with zero per-item friendship or consent SQL queries, and `friends_only` / `FederationConsent.federated_collection == False` items MUST obey identical visibility rules as `_get_sparql_items`.

### Requirement: Synchronized Item Visibility and Hidden State
The system SHALL keep `Item.visibility` and `Item.is_hidden` synchronized upon construction and update, ensuring `is_hidden=True` defaults `visibility` to `"private"` (unless explicitly given), `visibility="private"` enforces `is_hidden=True`, and friend-scoped item search (`GET /api/items?scope=friends&q=...`) matches both `is_hidden=False` and `visibility in ('public', 'friends_only', 'shared')`.

#### Scenario: Setting visibility to private hides item automatically

- **WHEN** an item's visibility is updated to `"private"`
- **THEN** `Item.is_hidden` becomes `True`

#### Scenario: Searching friends' items with a text query

- **WHEN** an authenticated user calls `GET /api/items?scope=friends&q=Dune`
- **THEN** the search matches items owned by accepted friends with `is_hidden=False` or `visibility in ('friends_only', 'shared')`, excluding private items

### Requirement: RDF and Graph Projection Relation Parity and Read-Only Federation Compatibility
Any RDF snapshot or SPARQL projection supporting catalog graph exploration SHALL emit complete FRBR/FRBRoo and semantic link coverage matching the catalog relation graph (`Work`, `Expression`, `Manifestation`, `Item`, `Contributor`, `WorkPart`, `WorkSeriesMembership`, `WorkExpansionLink`, `ContainerAggregation`, stable map attachment identifiers, and `SemanticLink` triples for `work`, `expression`, and `manifestation` strictly filtered to `status == "accepted"`), while remaining permitted for read-only exploration under `FEDERATION_HEAD_MODE=true`.

#### Scenario: Emitting expansion, container aggregation, and accepted expression semantic links in RDF snapshots

- **WHEN** an RDF collection snapshot is constructed from entities containing a `WorkExpansionLink`, a `ContainerAggregation`, an accepted `Expression`-scoped `SemanticLink`, and a pending `SemanticLink`
- **THEN** the resulting RDF graph MUST include triples for the `WorkExpansionLink`, `ContainerAggregation`, and accepted `Expression` `SemanticLink`, and MUST omit the pending `SemanticLink`.

#### Scenario: Serving read-only SPARQL and RDF graph queries in FEDERATION_HEAD_MODE

- **GIVEN** an instance running with `FEDERATION_HEAD_MODE=true`
- **WHEN** an authorized client issues read-only SPARQL `SELECT`/`ASK`/`CONSTRUCT`/`DESCRIBE` queries or catalog graph explorer requests
- **THEN** read-only graph and SPARQL queries MUST succeed without triggering the physical `Item` write `403` guard, while still enforcing `Item` three-tier visibility and `FederationConsent`.
