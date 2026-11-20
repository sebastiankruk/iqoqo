## Why

The Principal + Gemini release review of `release/1.1.0` (`.context/notes/review/1.1.0/principal-review-release-1.1.0.md`) cataloged nine low-severity query hygiene, RDF hardening, serial edge-case, and frontend polish items that do not block tagging `v1.1.0`. Scheduling them cleanly as `C137` for `v1.1.1` keeps `v1.1.0` focused on critical/moderate fixes while preventing technical debt from slipping through the cracks.

## What Changes

- **Shared Collection Lookup & SSR Cache Hygiene:** Return `(items, is_private_cache)` from a single DB query pass in `app/api/public_items.py` / `app/api/public_rdf.py`, and prevent Next.js `getSharedCollection()` (`frontend/lib/share-server.tsx`) from caching `friends_and_public`/`all` share tokens for 60s on cookieless SSR requests when the backend returns `Cache-Control: private, no-store`.
- **Deterministic Work Reading Rollup & SA 2.0 Cleanup:** Add deterministic tie-breaking for equal-rank statuses (`read` vs `listened`) and skip unmapped rank-0 statuses (`"unread"` / legacy strings) in `compute_work_reading_rollup()` (`app/core/frbr_service.py`), and replace legacy `db.session.query(Item.id)` in `app/api/works.py` `work_read_status` EXISTS subqueries with SQLAlchemy 2.0 `select(Item.id)`.
- **Serial RDF, Expression-Scoped Dedupe & Outbound Telemetry:** Forward `publication_year` in `build_collection_rdf_graph` dict branch and guard `int()` casts in `_emit_serial_rdf_triples()` (`app/core/frbr_service.py`), scope `(issue_number, publication_year)` dedupe to `Manifestation.expression_id == expression.id` (`app/core/ingest.py`), allow weekly EAN-2 add-ons `1..53` (`app/utils/issn.py`), and add `record_outbound_telemetry` spans/metrics to serial fetchers (`app/strategies/serials.py`).
- **Vision Status & Headline Polish:** Replace hardcoded `"national geographic"` in `_pick_serial_headline()` with the dynamically resolved serial title, and refine `vision_ready` reporting for Ollama-only deployments when `probe_ollama=False` (`app/utils/vision.py`).
- **Distinct Item Count & Collection Bulk UX Polish:** Use `COUNT(DISTINCT Item.id)` for `total_physical` in `get_items()` (`app/api/items.py`), clear `selectedItemIds` on filter/query/scope/viewMode changes in `frontend/app/collection/page.tsx`, and close the `BulkItemVisibilityToolbar` dropdown on outside click or `Escape`.

## Capabilities

### New Capabilities

- `v111-post-release-polish`: Post-`v1.1.0` low-severity query hygiene, RDF/serial edge-case hardening, and collection bulk UX polish (`C137`).

### Modified Capabilities

## Impact

- **Backend:** `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/works.py`, `app/api/items.py`, `app/core/frbr_service.py`, `app/core/ingest.py`, `app/utils/issn.py`, `app/strategies/serials.py`, `app/utils/vision.py`.
- **Frontend:** `frontend/lib/share-server.tsx`, `frontend/app/collection/page.tsx`, `frontend/components/collection/bulk-item-visibility-toolbar.tsx`.
- **Tests:** `tests/test_api_public_extended.py`, `tests/test_work_reading_rollup.py`, `tests/test_serial_ontology.py`, `tests/test_issn_and_serial_lookup.py`, `tests/test_vision.py`, `frontend/__tests__/components/collection/bulk-item-visibility.test.tsx`.
