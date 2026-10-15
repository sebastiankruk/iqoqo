## 1. Celery Background FTS Re-indexing

- [ ] Implement Redis entity queue and Celery batch FTS task in `app/core/tasks.py`.
- [ ] Update item/manifestation write handlers to enqueue re-indexing.
- [ ] Write tests in `tests/test_async_fts_transitions.py`.

## 2. Server-Sent Events Stream & UI Cache Refresh

- [ ] Implement `GET /api/v1/events/stream` in `app/api/events.py`.
- [ ] Wire frontend event listener to invalidate TanStack Query keys.
- [ ] Write tests in `tests/test_sse_events.py`.

