## 1. Celery Background FTS Re-indexing

- [x] Implement Redis entity queue and Celery batch FTS task in `app/core/tasks.py`.
- [x] Update item/manifestation write handlers to enqueue re-indexing.
- [x] Write tests in `tests/test_async_fts_transitions.py`.

## 2. Server-Sent Events Stream & UI Cache Refresh

- [x] Implement `GET /api/v1/events/stream` in `app/api/events.py`.
- [x] Wire frontend event listener to invalidate TanStack Query keys.
- [x] Write tests in `tests/test_sse_events.py`.

