## Why

Collectors who manage mixed-visibility libraries (`public`, `friends_only`, and `private`/hidden physical `Item`s) currently have no way to filter their `/collection` view by visibility tier or update visibility across multiple selected physical items in one operation.

## What Changes

- **Backend Collection Visibility Filtering (`GET /api/items`, `SearchService.search_items`, `/api/stats/facets`)**:
  - Add an optional `visibility` query parameter accepting comma-separated values (`public`, `friends_only`, `private`, plus `hidden` alias mapping to `private`/hidden items) enforced via SQL `WHERE` clauses and SQL `LIMIT`/`OFFSET` pagination.
  - Ensure non-owner callers (`scope=friends`, `scope=global`, or `include_public=true`) can NEVER bypass owner privacy to filter or reveal another user's `private`/`hidden` items.
- **Backend Bulk Visibility Mutation (`PATCH /api/items/bulk-visibility`)**:
  - Add an authenticated endpoint accepting `{ "item_ids": [int, ...], "visibility": "public" | "friends_only" | "private" }` (capped to bounded batch size, e.g., `<= 100` IDs).
  - Enforce `@require_permission(PermissionName.WRITE_ITEM)`, `reject_if_federation_head_item_write()`, and strict ownership (`Item.owner_id == current_user_id`), updating each `Item` via `item.set_visibility(visibility)` (keeping `is_hidden` synchronized), invalidating facet caches, and queuing FTS/ActivityPub updates.
  - Document the new `visibility` filter parameter and `PATCH /api/items/bulk-visibility` endpoint in `app/api/docs.py` (OpenAPI 3.1).
- **Frontend Collection Visibility Filter & Multi-Select Bulk Toolbar (`frontend/`)**:
  - Add a Visibility filter group in `SidebarFilters` / `FilterBar` (`Public`, `Friends Only`, `Private / Hidden`) synchronized with URL query parameters (`visibility=...`) and `en.json`/`pl.json`.
  - Enable multi-select mode in `viewMode === "items"` on `/collection` with a floating bulk item toolbar offering `"Change Visibility"` (`Public`, `Friends Only`, `Private`) actions.

## Capabilities

### New Capabilities
- `collection-visibility-management`: SQL-paginated filtering by visibility tier (`public`, `friends_only`, `private`/`hidden`) and owner-scoped bulk visibility mutation across physical `Item`s in the collection API and `/collection` UI.

### Modified Capabilities

## Impact

- **Backend (`app/`)**: `app/api/items.py`, `app/core/search_service.py`, `app/api/schemas.py`, `app/api/docs.py`.
- **Frontend (`frontend/`)**: `frontend/app/collection/page.tsx`, `frontend/components/collection/sidebar-filters.tsx`, `frontend/components/collection/filter-bar.tsx`, `frontend/components/collection/collection-grid.tsx` / bulk item toolbar component, `frontend/lib/api/hooks/catalog.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_api_visibility.py`, `tests/test_openapi_spec.py`, Vitest collection filter/bulk-visibility tests, Playwright E2E collection visibility test.
