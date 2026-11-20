## Context

See `proposal.md` for motivation. `Item` in `app/db/core.py` already enforces `ITEM_VISIBILITIES = ("public", "friends_only", "shared", "private")` and keeps `is_hidden` synchronized via `item.set_visibility(vis)`. On the frontend, `frontend/app/collection/page.tsx` currently enables multi-select (`selectedManifestations` + `BulkAddToolbar`) only in `viewMode === "manifestations"`, whereas physical items are managed in `viewMode === "items"`.

## Goals / Non-Goals

**Goals:**
- Provide fast, SQL-paginated filtering by `Item.visibility` across both SQLAlchemy listing (`GET /api/items`) and `SearchService.search_items()`.
- Provide an atomic, ownership-verified `PATCH /api/items/bulk-visibility` endpoint (capped at `100` items per request) with OpenAPI 3.1 schema parity.
- Support multi-select on physical `Item`s in `/collection` (`viewMode === "items"`) without conflating physical `Item` mutations with catalog `Manifestation` bulk-add (`BulkAddToolbar`).

**Non-Goals:**
- Changing visibility on `Work`, `Expression`, or `Manifestation` rows (visibility is strictly an `Item` ownership property in FRBR).
- Allowing batch size > 100 items in a single synchronous HTTP call.

## Decisions

1. **Map `"hidden"` query alias to `visibility == "private"` (`or_(Item.visibility == "private", Item.is_hidden.is_(True))` when scoped safely):** Users frequently refer to private items as "hidden" (`is_hidden`); supporting `visibility=hidden` alongside `visibility=private` in `GET /api/items` prevents UI/API mismatch while storing canonical `"private"`, `"friends_only"`, or `"public"` on writes.
2. **All-or-nothing ownership check in `PATCH /api/items/bulk-visibility`:** Verify `count(owned matching items) == len(unique item_ids)` before mutating any row. Reject with HTTP `403` if any `item_id` belongs to another user (or `404` if missing), preventing partial ambiguous state.
3. **Separate `BulkItemVisibilityToolbar` (or mode-aware bulk toolbar) for `viewMode === "items"`:** Keeps `BulkAddToolbar` strictly typed to `CatalogEntry` manifestations while giving `viewMode === "items"` clean multi-select visibility controls.

## Risks / Trade-offs

- **Offline / mobile read-only cache interaction** → When `visibility` filter is active or offline, guard `saveCollectionSnapshot()` per `C114b` rules (only unfiltered personal `items` snapshots overwrite the offline cache) and disable bulk visibility mutation while offline or in `FEDERATION_HEAD_MODE`.
