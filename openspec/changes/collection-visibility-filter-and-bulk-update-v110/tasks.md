## 1. Backend Visibility Filtering & Bulk Endpoint

- [x] 1.1 Add `visibility` filter support (`public`, `friends_only`, `private`, and `hidden` alias) to `GET /api/items` (`app/api/items.py`) and `SearchService.search_items()` (`app/core/search_service.py`) using SQL-level `WHERE` clauses prior to `LIMIT`/`OFFSET`, ensuring non-owner scopes (`friends`, `global`, `include_public`) never expose another user's `private` items; verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_api_visibility.py`
- [x] 1.2 Add `BulkItemVisibilitySchema` in `app/api/schemas.py` (`item_ids` bounded `1..100`, `visibility` in `{"public", "friends_only", "private"}`), implement `PATCH /api/items/bulk-visibility` in `app/api/items.py` with `@require_auth`, `@require_permission(PermissionName.WRITE_ITEM)`, `reject_if_federation_head_item_write()`, all-or-nothing ownership verification, `item.set_visibility()`, facet cache invalidation, and background FTS/ActivityPub sync; verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_api_visibility.py`
- [x] 1.3 Document `visibility` query parameter on `GET /api/items` and `PATCH /api/items/bulk-visibility` request/response schemas in `app/api/docs.py`, and verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_openapi_spec.py`

## 2. Frontend Collection Filters & Bulk Visibility UI

- [x] 2.1 Add `"visibility"` to `FilterType` / `chipLabel` in `frontend/components/collection/filter-bar.tsx`, add Visibility filter controls (`Public`, `Friends Only`, `Private / Hidden`) in `frontend/components/collection/sidebar-filters.tsx` and `frontend/app/collection/page.tsx` (URL-synced and passed to `useItems` hook in `frontend/lib/api/hooks/catalog.ts`), with EN/PL keys in `frontend/messages/en.json` and `frontend/messages/pl.json`
- [x] 2.2 Enable multi-select checkboxes on owned `Item`s in `viewMode === "items"` in `frontend/app/collection/page.tsx` and `frontend/components/collection/collection-grid.tsx`, add a bulk visibility toolbar component wired to `PATCH /api/items/bulk-visibility` (invalidating `items` & `facetStats` queries), and verify via `cd frontend && npx vitest run __tests__/components/collection/`

## 3. End-to-End Verification

- [x] 3.1 Add Playwright E2E test coverage for filtering `/collection` by visibility tier and bulk-updating item visibility, and verify full lint and parallel tests pass (`IQOQO_AI_MODE=1 make lint && IQOQO_AI_MODE=1 make test-parallel`)
