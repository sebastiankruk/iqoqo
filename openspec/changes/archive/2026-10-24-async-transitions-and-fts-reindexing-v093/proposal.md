## Why
Synchronous `tsvector` recomputation during item status, custody, and collection transitions causes write latency and database lock contention.
## What Changes

- Decouple `fts_vector` recomputations from synchronous write transactions.
- Queue entity IDs in Redis and batch-update `fts_vector` in Celery background task (`app/core/tasks.py`).
- Expose `GET /api/v1/events/stream` Server-Sent Events (SSE) transition stream.
- Update frontend TanStack Query caches reactively on transition completion without polling.

## Capabilities

### New Capabilities
- `async-transitions-fts-indexing`: Asynchronous PostgreSQL full-text search re-indexing via Celery and Server-Sent Events real-time transition stream

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Decouples heavy writes from HTTP threads; adds SSE endpoint.
