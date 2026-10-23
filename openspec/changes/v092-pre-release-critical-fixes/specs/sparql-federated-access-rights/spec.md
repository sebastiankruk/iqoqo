## ADDED Requirements

### Requirement: SQL-Pushed SPARQL Friend Scoping and Three-Tier Visibility Enforcement
The system SHALL resolve accepted local friend UUIDs via `get_friend_user_ids(user.id)` in `_get_sparql_items`, push owner, friend (`visibility in ('public', 'friends_only', 'shared')`), and public visibility predicates into the SQL `WHERE` clause prior to `LIMIT`, and preserve accepted friends' `friends_only` items during `build_graph` without executing per-item N+1 SQL queries.

#### Scenario: Accepted friend queries a friend's friends_only item via SPARQL
- **WHEN** an authenticated user executes a `SELECT` query on `/sparql` matching an item owned by an accepted local friend with `visibility="friends_only"`
- **THEN** the item's triples are included in the SPARQL snapshot and returned in the query results, while the friend's `private` items remain excluded

### Requirement: Synchronized Item Visibility and Hidden State
The system SHALL keep `Item.visibility` and `Item.is_hidden` synchronized at model initialization (`Item(..., is_hidden=True)` sets `visibility="private"`) and SHALL enforce `scope="friends"` filtering across both standard and full-text search (`q=...`) queries.

#### Scenario: Item instantiated with is_hidden=True is never exposed to friends
- **WHEN** an `Item` is created with `is_hidden=True` and default `visibility`
- **THEN** `item.visibility` is `"private"` and the item is excluded from friend-scoped `/api/items`, `/api/stats`, `/public/u/<username>/items`, and `/sparql` responses

### Requirement: Public RDF Visibility and Consent Gates
The system SHALL evaluate `user.visibility` (`private` / `friends_only`) and friend authorization before serving RDF content-negotiated responses on `/public/u/<username>/items`, SHALL exclude hidden/non-public items from `serialize_user_collection_to_rdf`, and SHALL enforce `is_item_publicly_visible(item)` on `/public/items/<id>/custody`.

#### Scenario: Requesting RDF collection for a private or friends_only user without authorization
- **WHEN** an unauthenticated client requests `GET /api/public/u/<username>/items?format=turtle` for a user with `visibility="private"` or `"friends_only"`
- **THEN** the system returns HTTP `404` without serializing any RDF triples
