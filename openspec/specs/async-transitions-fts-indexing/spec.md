# async-transitions-fts-indexing Specification

## Purpose
Asynchronous PostgreSQL full-text search re-indexing via Celery and Server-Sent Events real-time transition stream.

## Requirements

### Requirement: Background FTS Vector Recomputation

The system SHALL queue and batch-update full-text search vectors asynchronously without blocking transition writes, coalescing rapid updates via a Redis `SET iqoqo:fts_reindex_scheduled 1 NX EX <countdown>` debounce lock, protecting `_in_memory_fts_queue` with a `threading.Lock`, refreshing `Work` entities in `batch_fts_reindex`, and closing short-lived Redis clients (`finally: client.close()`) in `publish_transition_event`, `enqueue_fts_reindex`, and `batch_fts_reindex`.

#### Scenario: Transition writes return immediately

- **WHEN** An item status or custody changes
- **THEN** The HTTP response returns 200 immediately, enqueuing Celery FTS re-indexing in background.

#### Scenario: Rapid writes within debounce window schedule a single Celery task

- **WHEN** Multiple item or manifestation updates occur within the 5-second debounce window
- **THEN** `enqueue_fts_reindex` adds all entity keys to `iqoqo:fts_reindex_queue` and schedules `batch_fts_reindex` only once while `iqoqo:fts_reindex_scheduled` is held.

#### Scenario: Short-lived Redis clients are closed on publish and queue operations

- **WHEN** `publish_transition_event`, `enqueue_fts_reindex`, or `batch_fts_reindex` acquires a Redis client via `get_redis_client()`
- **THEN** The client is closed inside a `finally` block after the operation completes or raises an exception.

#### Scenario: Background FTS task recomputes search vectors for affected works

- **WHEN** the background FTS re-indexing task drains queued `work`, `manifestation`, or `item` entries
- **THEN** the worker resolves the parent Work records and executes a database update refreshing their full-text search vectors so updated titles and metadata become searchable

#### Scenario: Private item re-index does not broadcast global cache invalidation to unrelated users

- **WHEN** User A updates a private item and the background FTS task completes
- **THEN** unrelated connected User B does not receive a cross-tenant `fts_reindexed` invalidation for User A's private item

### Requirement: Per-User SSE Transition Stream Isolation and Resource Bounds

The SSE stream (`GET /api/v1/events/stream`) SHALL run under multi-threaded HTTP workers so concurrent SSE connections cannot starve synchronous API endpoints, SHALL clamp `timeout` strictly below the HTTP worker timeout (`[1.0, 20.0]` seconds) with `math.isfinite` validation, SHALL fail closed for user-scoped events (`item_created`, `item_updated`, `item_deleted`, `custody_lent`, `custody_returned`, and owner-scoped `fts_reindexed`) when `user_id` is absent or belongs to neither the owner nor the borrower, SHALL reuse pooled or cleanly closed Redis connections across publishing and streaming, SHALL emit `item_created` on `POST /api/item/<isbn>`, and SHALL connect the browser `EventSource` listener only when an authenticated user session is active on non-public routes while invalidating `["facetStats"]`, `["globalStats"]`, `["collectionGrid"]`, `["items"]`, `["manifestations"]`, and `["stats"]`.

#### Scenario: Private item transition is not streamed to other users

- **WHEN** User A creates, updates, or deletes an item while User B is connected to `GET /api/v1/events/stream`
- **THEN** User A receives the transition event over SSE and User B does not receive User A's private item transition event

#### Scenario: Unbounded or non-finite SSE timeout is clamped

- **WHEN** a client requests `GET /api/v1/events/stream?timeout=60` or `?timeout=inf`
- **THEN** the server clamps the streaming duration to at most `20.0` seconds and closes the stream gracefully before the HTTP server worker timeout elapses

#### Scenario: Unauthenticated visitor on public route does not open SSE stream

- **WHEN** an unauthenticated visitor loads `/login`, `/register`, or `/share/<token>`
- **THEN** the web client does not open a `GET /api/v1/events/stream` `EventSource` connection or trigger background `401` polling
