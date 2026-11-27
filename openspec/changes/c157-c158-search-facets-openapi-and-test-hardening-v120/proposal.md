## Why

A `/test-craftsman` QA audit across `v1.2.0` (`C154`–`C158`, `C163`–`C164`) uncovered several live runtime/contract bugs masked by test gaps, deleted/vacuous unit tests, and missing Playwright E2E coverage:

1. **PostgreSQL crash & missing DTO field on `q` + `location` search (`C157`):** `app/core/search_service.py` adds `AND i.physical_location IN :location_filter` to the raw SQL FTS query without `bindparam("location_filter", expanding=True)`, causing SQL execution errors on PostgreSQL; `rows_sql`, `_ilike_item_search`, and `app/api/items.py` (`if q:`) also omit `physical_location`.
2. **Faceted stats ignoring `?location=...` filter (`C157`):** `app/core/data_manager.py` accepts `locations` in `get_faceted_stats` and records it in `cache_params`, yet `_compute_faceted_stats` never passes `locations` to `_build_item_ids_subq`, and `loc_query` filters against `tag_subq` rather than `loc_subq`.
3. **Collection URL state dropping `location` (`C157`):** `frontend/lib/collection-url.ts` omits `["location", "location"]` from `MULTI_VALUE_PARAMS`, dropping `?location=...` on `/collection` reload and shared links.
4. **OpenAPI 3.1 contract drift (`C157`, `C158`, `C164`):** `app/api/docs.py` declares an unwrapped `200` schema for `GET /api/manifestations/{id}/stats` (actual returns `{success, data, error}`), omits `Item.physical_location` and `?location=` on `/items` and `/stats/facets`, and lacks endpoint assertions in `tests/test_openapi_contract_completeness.py`.
5. **Vacuous/deleted unit tests & zero Playwright E2E for `v1.2.0` flows:** `bottom-sheet.test.tsx` timeout test silently executes zero assertions (`queryByRole("textbox")` is `null`); `server-selector.test.tsx` lost 4 existing connection/validation tests; native `storage.test.ts` & `offline-cache.test.ts` multi-server tests, C157 UI component tests (`bulk-item-visibility`, `edit-item-dialog`, `sidebar-filters`), `test_isbn.py` clock tests, `cloud_backup*.bats` monthly thresholds/fallback, and Playwright E2E specs for `C156`/`C157`/`C158`/`C164` are missing.

## What Changes

- **Search, Facets & URL Round-Trip Fixes:**
  - Bind `bindparam("location_filter", expanding=True)` on FTS queries and include `physical_location` in `SearchService` & `GET /api/items?q=` responses.
  - Thread `locations` through `DataManager._compute_faceted_stats` -> `_build_item_ids_subq` and fix `loc_query` using `loc_subq`.
  - Add `["location", "location"]` to `frontend/lib/collection-url.ts` (`MULTI_VALUE_PARAMS`) with `FilterType` exhaustiveness tests.
- **OpenAPI 3.1 Schema & Contract Sync:**
  - Wrap `/api/manifestations/{id}/stats` `200` schema in `{success, data, error}`, add `physical_location` to `Item`, `?location=` to `/items` & `/stats/facets`, document `/api/manifestations/{id}/images`, and assert all `v1.2.0` contracts in `tests/test_openapi_contract_completeness.py`.
- **Unit, BATS & Playwright E2E Hardening:**
  - Fix vacuous `bottom-sheet.test.tsx` test + add `ScanPage` 15s timeout abort test; restore 4 deleted `server-selector.test.tsx` tests + native `storage.test.ts` / `offline-cache.test.ts` multi-server isolation; add C157 unit tests (`bulk-item-visibility`, `edit-item-dialog`, `sidebar-filters`, `taxonomy-editor-location`, `test_item_location.py` 400/404/clear/RDF, `test_migration.py`); expand `test_isbn.py`, `test_manifestation_stats.py`, `test_catalog_graph_api.py`, `test_s3_service.py`, and `cloud_backup*.bats`; remove disallowed lint suppressions (`manifestation-covers-and-stats.test.tsx`, `test_s3_service.py`); and add Playwright E2E specs for `v1.2.0` UI workflows.

## Impact

- Affected files: `app/core/search_service.py`, `app/core/data_manager.py`, `app/api/items.py`, `app/api/docs.py`, `frontend/lib/collection-url.ts`, backend/frontend/BATS/Playwright test suites.
- Resolves real PostgreSQL search crash, broken facet filtering, broken URL bookmarking, and OpenAPI schema drift prior to tagging `v1.2.0`.
