## ADDED Requirements

### Requirement: Per-User SSE Transition Stream Isolation and Resource Bounds

The SSE stream (`GET /api/v1/events/stream`) SHALL filter user-scoped transition events (`item_created`, `item_updated`, `item_deleted`, `custody_lent`, `custody_returned`) so they are only delivered to the item's owner or borrower, SHALL clamp `timeout` to `[1.0, 60.0]` seconds with `math.isfinite` validation, SHALL close Redis clients in `finally` blocks, SHALL emit `item_created` and enqueue FTS reindexing on `POST /api/item/<isbn>`, and SHALL invalidate `["facetStats"]`, `["globalStats"]`, `["collectionGrid"]`, `["items"]`, `["manifestations"]`, and `["stats"]` in `TransitionEventsListener`.

#### Scenario: Private item transition is not streamed to other users

- **WHEN** User A creates, updates, or deletes an item while User B is connected to `GET /api/v1/events/stream`
- **THEN** User A receives the transition event over SSE and User B does not receive User A's private item transition event

#### Scenario: Unbounded or non-finite SSE timeout is clamped

- **WHEN** a client requests `GET /api/v1/events/stream?timeout=86400` or `?timeout=inf`
- **THEN** the server clamps the streaming duration to at most `60.0` seconds
