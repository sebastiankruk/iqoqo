## MODIFIED Requirements

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
