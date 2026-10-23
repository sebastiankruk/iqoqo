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
The system SHALL resolve accepted local friend UUIDs via `get_friend_user_ids(user.id)` in `_get_sparql_items`, push owner, friend (`visibility in ('public', 'friends_only', 'shared')`), and public visibility predicates into the SQL `WHERE` clause prior to `LIMIT`, and preserve accepted friends' `friends_only` items during `build_graph` without executing per-item N+1 SQL queries.

#### Scenario: Accepted friend queries a friend's friends_only item via SPARQL

- **WHEN** an authenticated user executes a `SELECT` query on `/sparql` matching an item owned by an accepted local friend with `visibility="friends_only"`
- **THEN** the item's triples are included in the SPARQL snapshot and returned in the query results, while the friend's `private` items remain excluded

### Requirement: Synchronized Item Visibility and Hidden State
The system SHALL keep `Item.visibility` and `Item.is_hidden` synchronized upon construction and update, ensuring `is_hidden=True` defaults `visibility` to `"private"` (unless explicitly given), `visibility="private"` enforces `is_hidden=True`, and friend-scoped item search (`GET /api/items?scope=friends&q=...`) matches both `is_hidden=False` and `visibility in ('public', 'friends_only', 'shared')`.

#### Scenario: Setting visibility to private hides item automatically

- **WHEN** an item's visibility is updated to `"private"`
- **THEN** `Item.is_hidden` becomes `True`

#### Scenario: Searching friends' items with a text query

- **WHEN** an authenticated user calls `GET /api/items?scope=friends&q=Dune`
- **THEN** the search matches items owned by accepted friends with `is_hidden=False` or `visibility in ('friends_only', 'shared')`, excluding private items
