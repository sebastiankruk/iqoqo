## Why

Collectors and bibliophiles want to know how long it takes them to read a book (both total elapsed days from start to finish and cumulative active reading session minutes) without polluting the FRBR `Work` or `Manifestation` layers with user-specific telemetry.

## What Changes

- **FRBR Item-Scoped Reading Session & Duration Model (`app/db/core.py` & `app/db/social.py`):** Keep reading duration strictly bound to the physical/owned `Item` (`F5_Item`) and `ReadingTransition` audit log: compute elapsed days between `currently_reading` (`started_at`) and `read` (`finished_at`) transitions, and store optional user reading sessions (`duration_minutes`, `pages_read`, `logged_at`) in `Item.meta["reading_sessions"]` (or dedicated `ItemReadingSession` relation) with aggregated `total_reading_minutes` on the Item.
- **Reading Duration API & Transition Hook (`app/api/items.py`, `app/api/manifestations.py`):** Expose `POST /api/items/<int:item_id>/reading-sessions` to log a timed or manual reading session, include `reading_duration_summary` (`total_minutes`, `sessions_count`, `started_at`, `finished_at`, `elapsed_days`) on `GET /api/items/<id>`, and surface anonymized aggregate average read time on `Manifestation` detail projections when consented.
- **Item Sidebar Reading Timer / Log UI (`frontend/components/item/reading-duration-card.tsx`):** Add a compact, low-density reading duration widget on the `/item/[id]` view when `status` is `currently_reading` or `read`, allowing 1-tap session timer start/stop or quick manual duration entry (`+15m`, `+30m`, `+1h`, custom).

## Capabilities

### New Capabilities
- `item-reading-duration-tracking`: FRBR `Item`-scoped reading session logging, start-to-finish transition duration calculation, and anonymized `Manifestation` average read-time projection.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- **Backend:** `app/api/items.py`, `app/api/manifestations.py`, `app/schemas/items.py`, `app/core/meta_display.py`
- **Frontend:** `frontend/components/item/reading-duration-card.tsx`, `frontend/components/item/item-sidebar.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- **Tests:** `tests/test_reading_duration.py`, `frontend/__tests__/components/item/reading-duration-card.test.tsx`
