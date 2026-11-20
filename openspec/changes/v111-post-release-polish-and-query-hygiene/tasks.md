## 1. Shared Collection Lookup & SSR Cache Hygiene

- [x] 1.1 Refactor `app/api/public_items.py` and `app/api/public_rdf.py` to return `(items, is_private_cache)` from a single DB query pass instead of calling `fetch_shared_collection_by_token()` and `is_shared_collection_private_cache()` separately; verify with `tests/test_api_public_extended.py`
- [x] 1.2 Update `getSharedCollection()` in `frontend/lib/share-server.tsx` so cookieless SSR requests do not retain private-scope (`friends_and_public`/`all`) share payloads in Next.js 60s ISR Data Cache after revocation; verify with `frontend/__tests__/components/collection/share-collection-dialog.test.tsx`

## 2. Deterministic Work Reading Rollup & SA 2.0 Cleanup

- [x] 2.1 Add deterministic tie-breaking for equal-rank statuses (`read` vs `listened`) and skip unmapped rank-0 statuses (`"unread"` / legacy values) in `compute_work_reading_rollup()` (`app/core/frbr_service.py`); verify with `tests/test_work_reading_rollup.py`
- [x] 2.2 Replace legacy `db.session.query(Item.id)` in `work_read_status` EXISTS subqueries (`app/api/works.py`) with SQLAlchemy 2.0 `select(Item.id)`; verify with `tests/test_work_reading_rollup.py`

## 3. Serial RDF, Expression-Scoped Dedupe & Outbound Telemetry

- [x] 3.1 Forward `"publication_year"` in `build_collection_rdf_graph`'s dict branch and guard `int()` casts in `_emit_serial_rdf_triples()` (`app/core/frbr_service.py`) against non-numeric legacy JSON strings; verify with `tests/test_serial_ontology.py`
- [x] 3.2 Scope `(issue_number, publication_year)` deduplication to `Manifestation.expression_id == expression.id` in `app/core/ingest.py`, allow weekly EAN-2 add-ons `1..53` in `app/utils/issn.py`, and wrap BN/Crossref/OpenLibrary fetchers in `app/strategies/serials.py` with `record_outbound_telemetry`; verify with `tests/test_issn_and_serial_lookup.py` and `tests/test_serial_scan_disambiguation.py`

## 4. Vision Polish, Distinct Item Count & Collection Bulk UX

- [x] 4.1 Filter `_pick_serial_headline()` (`app/utils/vision.py`) against the dynamically resolved serial title instead of hardcoded `"national geographic"`, and refine `vision_ready` for configured Ollama-only deployments when `probe_ollama=False`; verify with `tests/test_vision.py`
- [x] 4.2 Use `func.count(func.distinct(Item.id))` for `total_physical` in `get_items()` (`app/api/items.py`) to prevent 1-to-many join overcounts; verify with `tests/test_api_visibility.py`
- [x] 4.3 Reset `selectedItemIds` on filter/query/scope/viewMode changes in `frontend/app/collection/page.tsx` and close the `BulkItemVisibilityToolbar` dropdown (`frontend/components/collection/bulk-item-visibility-toolbar.tsx`) on outside click or `Escape`; verify with `frontend/__tests__/components/collection/bulk-item-visibility.test.tsx`

## 5. Verification

- [x] 5.1 Run `IQOQO_AI_MODE=1 make secret-scan && IQOQO_AI_MODE=1 make lint && IQOQO_AI_MODE=1 make test-parallel` and verify all 4 test streams pass cleanly
