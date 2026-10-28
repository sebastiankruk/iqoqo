## MODIFIED Requirements

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
