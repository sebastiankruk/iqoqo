## Context

See `proposal.md` for motivation. `iqoqo` already records status transitions (`want_to_read` $\to$ `currently_reading` $\to$ `read`) in `ReadingTransition` (`app/db/core.py`). Extending `Item` with structured reading session logs (`reading_sessions` + `total_reading_minutes`) and computing elapsed days from `ReadingTransition` satisfies the user's request to track how long users read a book while strictly respecting FRBR boundaries.

## Goals / Non-Goals

**Goals:**
- Attach reading session logs and start-to-finish duration strictly to `Item` (`F5_Item`), never mutating `Work` or `Manifestation` directly with personal reading state.
- Provide a clean, low-button-density `ReadingDurationCard` in the `/item/[id]` sidebar (visible to the owner for `text` category items).
- Compute SQL aggregate `AVG(total_reading_minutes)` for public items on `Manifestation` detail views using a single `GROUP BY` / aggregate query (no N+1 loops).

**Non-Goals:**
- Real-time server-side WebSocket timers (any active stopwatch runs locally in browser `localStorage` and submits a single `POST /api/items/<id>/reading-sessions` on stop).

## Decisions

### 1. Bounded `Item.meta["reading_sessions"]` + `total_reading_minutes` with Pydantic Validation
* **Decision:** Validate payloads via `ReadingSessionCreateSchema` (`duration_minutes: int` constrained to `1..1440`, optional `pages_read: int` `1..5000`, optional `note: str` max `280` chars) and cap stored recent session entries at `200` per item while maintaining cumulative `total_reading_minutes` and `sessions_count`.
* **Rationale (Security & SRE):** Prevents unbounded JSONB growth (`DoS`) while requiring zero destructive schema migrations.

## Risks / Trade-offs

- **[Risk] Button clutter on `/item/[id]`** $\to$ **Mitigation:** Collapse quick-add presets (`+15m`, `+30m`, `+1h`) inside a single compact popover/modal opened from one `"Log Reading Time"` button inside `ReadingDurationCard`.
