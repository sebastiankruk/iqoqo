## 1. Inbox and Outbox Route Implementation

- [ ] Implement inbox and outbox route handlers in `app/api/federation.py`.
- [ ] Enforce rate limits and payload caps in `app/core/limiter.py`.

## 2. Activity Handlers & Celery Queue Setup

- [ ] Implement handlers in `app/core/federation_handlers.py`.
- [ ] Configure `federation` Celery queue in `app/core/celery_app.py`.
- [ ] Write backend tests in `tests/test_federation_inbox_outbox.py`.

