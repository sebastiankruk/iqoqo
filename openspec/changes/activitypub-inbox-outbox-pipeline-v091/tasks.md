## 1. Inbox and Outbox Route Implementation

- [x] Implement inbox and outbox route handlers in `app/api/federation.py`.
- [x] Enforce rate limits and payload caps in `app/core/limiter.py`.

## 2. Activity Handlers & Celery Queue Setup

- [x] Implement handlers in `app/core/federation_handlers.py`.
- [x] Configure `federation` Celery queue in `app/core/celery_app.py`.
- [x] Write backend tests in `tests/test_federation_inbox_outbox.py`.

