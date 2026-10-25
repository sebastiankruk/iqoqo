## Context

During the PR #376 (`release/0.9.3` → `main`) code review, several non-blocking `MODERATE` and `LOW` polish items were identified across `C84`, `C85`, `C86`, and `C87`:
1. `requirements.txt` and `pyproject.toml` pin `boardgamegeek>=0.13.0` instead of `boardgamegeek2>=1.3`, `BGGBackoffAdapter.send` in `app/utils/bgg.py` sleeps for raw `Retry-After` headers without an upper bound and stacks retries with `BoardGameGeek(..., retries=3)`, and `scripts/iqoqo-status.sh` interpolates bash variables directly into `python3 -c` strings.
2. `enqueue_fts_reindex` in `app/core/tasks.py` calls `batch_fts_reindex.apply_async` on every single write rather than coalescing scheduling via a Redis `SET ... NX EX` debounce lock, mutates `_in_memory_fts_queue` without a lock, and does not touch `Work` rows in `batch_fts_reindex`.
3. `app/api/docs.py` types `User.id`, `Item.owner_id`, and `Notification.recipient_id` as `integer` instead of UUID strings, defines `revoked` instead of `is_active`/`revoked_at` on `PersonalAccessToken`, uses a brittle path-prefix heuristic for `requires_auth`, and `docs/gems/iqoqo-librarian-gem.md` references `/api/scanner/lookup` instead of `/api/scanner/preview/{barcode}`.
4. `TotpSetup` and `PatManagement` on `/profile` contain hardcoded English strings instead of using `useTranslations("Profile")`.

## Goals / Non-Goals

**Goals:**
- Upgrade `boardgamegeek2>=1.3`, cap `Retry-After` sleep at `10.0` seconds, avoid stacked retries, and harden `scripts/iqoqo-status.sh` variable passing.
- Coalesce `batch_fts_reindex` Celery task dispatches via a Redis `NX EX` debounce lock, protect `_in_memory_fts_queue` with a lock, and refresh `Work` FTS state.
- Align OpenAPI 3.1 component schemas (`User`, `Item`, `Notification`, `PersonalAccessToken`, `Expression`) and decorator-based `_requires_auth` detection in `app/api/docs.py`, and sync `docs/gems/iqoqo-librarian-gem.md`.
- Localize `TotpSetup` and `PatManagement` in `en.json` and `pl.json` via `useTranslations("Profile")`.

**Non-Goals:**
- Critical security and functional blockers for `v0.9.3` (handled immediately in `v093-pre-release-critical-fixes`).

## Decisions

1. **Redis Debounce Lock in `enqueue_fts_reindex` (`app/core/tasks.py`)**:
   - After `client.sadd(REDIS_FTS_QUEUE_KEY, key)`, check `client.set("iqoqo:fts_reindex_scheduled", "1", nx=True, ex=max(1, countdown))` (when `not celery.conf.task_always_eager`) before calling `batch_fts_reindex.apply_async(countdown=countdown, retry=False)`, and delete `"iqoqo:fts_reindex_scheduled"` inside `batch_fts_reindex` when draining the queue.
2. **Decorator Attribute `_requires_auth` (`app/api/decorators.py` & `app/api/docs.py`)**:
   - Set `decorated._requires_auth = True` inside `require_auth`, `admin_required`, and `admin_or_custodian_required`, and inspect `getattr(view_func, "_requires_auth", False)` in `assemble_complete_openapi_spec()`.

## Risks / Trade-offs

- **Eager Celery mode in unit tests**: When `celery.conf.task_always_eager` is `True`, `batch_fts_reindex` executes synchronously during `apply_async` and clears the lock immediately, so tests remain deterministic.
