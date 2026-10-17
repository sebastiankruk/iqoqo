## Why
Enables server-to-server ActivityPub message processing for collections, follows, and catalog updates on dedicated background queues.
## What Changes

- Implement `POST /api/federation/actor/{username}/inbox` and `POST /api/federation/inbox` (shared inbox).
- Implement paginated `GET /api/federation/actor/{username}/outbox` (`OrderedCollection`).
- Create `app/core/federation_handlers.py` handling `Follow`, `Undo`, `Accept`, `Reject`, `Create`, `Update`, `Delete`, `Announce`.
- Create `app/core/federation_dispatch.py` and Celery tasks in `app/core/federation_tasks.py`.
- Route federation tasks to dedicated `federation` Celery queue with 100KB payload limit and `Flask-Limiter` rates.

## Capabilities

### New Capabilities
- `activitypub-inbox-outbox`: ActivityPub Actor/Shared Inboxes, read-only Outbox, async handlers, and Celery queue fan-out

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Adds asynchronous S2S activity pipeline and background worker routing.
