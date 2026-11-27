# c157-c158-search-facets-openapi-and-test-hardening Specification

## Purpose
Resolve `C157`/`C158` search, facet, URL-sync, and OpenAPI 3.1 contract bugs and close unit, BATS, and Playwright E2E test gaps across `v1.2.0`.

## Requirements

### Requirement: Combined Text Search and Location Filter Stability

`SearchService` and `GET /api/items?q=...&location=...` MUST safely bind expanding `location_filter` parameters on PostgreSQL FTS queries and include owner/admin-authorized `physical_location` in search results.

#### Scenario: Searching items by keyword and physical location

- **GIVEN** an authenticated owner with items in `"Living Room / Shelf A"` and `"Basement Box"` matching query `"Solaris"`
- **WHEN** `GET /api/items?q=Solaris&location=Living+Room+%2F+Shelf+A` executes on SQLite or PostgreSQL
- **THEN** the response MUST succeed with `200`, use `bindparam("location_filter", expanding=True)` on raw FTS SQL, return only matching items in that location, and include `physical_location` for owned items

### Requirement: Location Filtering in Faceted Stats and Collection URL Sync

`GET /api/stats/facets?location=...` and `/collection` URL serialization MUST honor active `location` filters end-to-end.

#### Scenario: Reloading collection page with location facet selected

- **GIVEN** a collector filters `/collection` by a `location` facet
- **WHEN** `buildCollectionUrl` serializes filters, the page reloads, and `parseCollectionUrl` / `GET /api/stats/facets?location=...` execute
- **THEN** `?location=...` MUST round-trip identically and `GET /api/stats/facets` MUST narrow facet counts using `locations` in `_build_item_ids_subq`

### Requirement: Strict OpenAPI 3.1 Contract and v1.2.0 E2E/Unit Parity

All `v1.2.0` API endpoints (`PATCH /api/items/bulk-location`, `?location=` parameters, `Item.physical_location`, `GET /api/manifestations/<id>/stats` envelope, `GET /api/manifestations/<id>/images`) MUST match OpenAPI 3.1 schemas in `app/api/docs.py`, and `v1.2.0` workflows MUST have non-vacuous unit, BATS, and Playwright E2E tests without disallowed lint suppressions.

#### Scenario: Verifying OpenAPI contract and v1.2.0 UI workflows

- **GIVEN** the generated `/api/docs/openapi.json` and `frontend/__tests__/e2e/` Playwright suite
- **WHEN** `tests/test_openapi_contract_completeness.py` and `make test-e2e` run
- **THEN** `/api/manifestations/{manifestation_id}/stats` `200` schema MUST use the `{success, data, error}` envelope, all `v1.2.0` endpoints MUST be asserted in OpenAPI contract tests, and Playwright E2E MUST verify physical location tagging/filtering, manifestation covers/stats, multi-server mobile switching, and `/graph` Person canonical LOD dedup
