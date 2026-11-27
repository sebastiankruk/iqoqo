## 1. Search, Facets & Collection URL Bugfixes

- [x] 1.1 Fix `app/core/search_service.py` FTS `bindparam("location_filter", expanding=True)` crash and add `physical_location` to FTS/ILIKE DTOs and `app/api/items.py` (`if q:`) search output
- [x] 1.2 Fix `app/core/data_manager.py` `_compute_faceted_stats` so `locations` filters `_build_item_ids_subq` and `loc_query` uses `loc_subq` instead of `tag_subq`
- [x] 1.3 Add `["location", "location"]` to `frontend/lib/collection-url.ts` (`MULTI_VALUE_PARAMS`) and exhaustiveness tests in `frontend/__tests__/lib/collection-url.test.ts`

## 2. OpenAPI 3.1 Contract Alignment (`app/api/docs.py`, `tests/test_openapi_contract_completeness.py`)

- [x] 2.1 Wrap `GET /api/manifestations/{manifestation_id}/stats` `200` schema in `{success, data, error}`, add `Item.physical_location`, `?location=` on `/items` & `/stats/facets`, and document `/api/manifestations/{manifestation_id}/images`
- [x] 2.2 Add `v1.2.0` endpoint, query param, and response schema assertions in `tests/test_openapi_contract_completeness.py`

## 3. Unit, BATS & E2E Test Hardening & Lint Cleanups

- [x] 3.1 Fix vacuous `bottom-sheet.test.tsx` timeout test, add `ScanPage` 15s timeout/abort test, and add `time.monotonic` wall-clock budget/BN gap-fill tests in `tests/test_isbn.py`
- [x] 3.2 Restore 4 deleted `server-selector.test.tsx` tests + add rename/active-delete/Footer-modal tests, plus native device `storage.test.ts` & `offline-cache.test.ts` multi-server isolation tests
- [x] 3.3 Add `C157` tests (`tests/test_item_location.py` `q+location`, `facets?location=`, 400/404/clear, RDF HTTP; `test_migration.py` up/down + PG index; `bulk-item-visibility.test.tsx`, `edit-item-dialog.test.tsx`, `sidebar-filters.test.tsx`, `taxonomy-editor-location.test.tsx`)
- [x] 3.4 Expand `C158`/`C163`/`C164` unit & BATS coverage (`friends_only`, non-book statuses, >12mo buckets, real hooks, `S3_BUCKET_BACKUP` fallback, monthly archive warn/fail thresholds, `storage_class` whitespace, hop-merge, empty URI, `frbr-relation-graph.test.tsx` `lod:<digest>`) and remove disallowed lint suppressions (`manifestation-covers-and-stats.test.tsx:33`, `test_s3_service.py:367`)
- [x] 3.5 Add Playwright E2E specs for `v1.2.0` flows (`physical_location` `/item/[id]` & `/collection`, `/manifestation/[id]` gallery + stats, mobile multi-server switcher, `/graph` Person canonical LOD dedup)
- [x] 3.6 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, `IQOQO_AI_MODE=1 make test-e2e`, and `IQOQO_AI_MODE=1 make secret-scan`
