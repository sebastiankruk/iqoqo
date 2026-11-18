## Why

Consumption/reading status (`want_to_read`, `reading`, `read`, `dnf`, `listened`, `watched`, `played`, `built`) is tracked per physical `Item` (`F5_Item`). When a collector views a different edition (`/manifestation/[id]`) or browses the conceptual `/work/[id]` page or global Works catalog (`/works/shelf`), iqoqo does not roll up that the collector has already consumed (or is currently consuming) that `Work` via another owned edition.

## What Changes

- **Backend User-Scoped Work Reading Status Rollup (`app/core/frbr_service.py`, `app/api/works.py`, `app/api/manifestations.py`, `app/api/docs.py`)**:
  - Add a batched `GROUP BY` helper `compute_work_reading_rollup(user_id, work_ids)` computing each user's highest-precedence Work-level status across all owned `Item`s (including private/hidden items owned by that caller, across all `Expression`s and `Manifestation`s of each `Work`) plus `completed_item_ids` / `completed_via_other_edition` hints.
  - Precedence order: completed (`read`, `listened`, `watched`, `played`, `built`) > active (`reading`, `listening`, `watching`, `playing`, `building`) > intent/unread (`want_to_read`, `want_to_listen`, `want_to_watch`, `want_to_play`, `want_to_build`, `dnf`).
  - Expose `work_reading_status` (and `completed_manifestation_ids`) on `GET /api/works/<id>`, `GET /api/works/shelf`, and `GET /api/manifestations/<id>` (authenticated callers only; `null` for unauthenticated callers), plus optional `work_read_status` filter on `GET /api/works/shelf` (`completed` / `in_progress` / `unread`).
  - Keep all `ReadingTransition` logs and `reading_sessions` strictly anchored to `Item` (`F5_Item`) — never storing personal reading state on `Work`.
- **Frontend Work & Manifestation Consumption Rollup Badges (`frontend/`)**:
  - Render localized `"Read"` / `"Read (via another edition)"` / `"Currently Reading"` (and media-appropriate `"Listened"`, `"Watched"`, `"Played"`, `"Built"`) badges on `/work/[id]`, `/manifestation/[id]`, and `Works` catalog cards.

## Capabilities

### New Capabilities
- `work-level-reading-status-rollup`: User-scoped, batched `GROUP BY` rollup of `Item` consumption statuses onto parent `Work` and sibling `Manifestation` views without mutating `Work`.

### Modified Capabilities

## Impact

- **Backend (`app/`)**: `app/core/frbr_service.py`, `app/api/works.py`, `app/api/manifestations.py`, `app/api/docs.py`.
- **Frontend (`frontend/`)**: `frontend/components/work/work-detail-client.tsx`, `frontend/components/manifestation/manifestation-detail-client.tsx`, `frontend/types/frbr.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_work_reading_rollup.py`, `tests/test_openapi_spec.py`, Vitest work/manifestation rollup badge tests.
