## 1. Shared Collection Visibility & Cache Safety (C129 Critical + Moderate)

- [x] 1.1 Fix `_build_shared_visibility_predicate()` and `SearchService.search_items()` `include_hidden` handling in `app/api/public_items.py` and `app/core/search_service.py` so `friends_only` items (`is_hidden=True`) are returned on `friends_and_public` shares and Friend Bonus shares while keeping `is_hidden=False` on `public` items; verify with regression tests in `tests/test_api_public_extended.py` and `tests/test_public_feeds.py`
- [x] 1.2 Emit `Vary: Authorization, Cookie` in `_apply_share_cache_headers()` on anonymous `public, max-age=300` responses in `app/api/public_items.py`; verify header presence in `tests/test_api_public_extended.py`

## 2. Bulk Visibility Security, Sync & Search Pinning (C128 Moderate)

- [x] 2.1 Filter `bulk_update_item_visibility()` in `app/api/items.py` by `Item.owner_id == user_id` and return a uniform error for missing or foreign item IDs to close the 404/403 BOLA oracle; verify with `tests/test_api_visibility.py`
- [x] 2.2 Dispatch ActivityPub federation update/delete and FTS synchronization when `bulk_update_item_visibility()` transitions items between `public` and non-public visibility; verify with `tests/test_api_visibility.py`
- [x] 2.3 Pin non-owned `include_public=True` rows in `SearchService._pg_item_fts` and `_ilike_item_search` (`app/core/search_service.py`) strictly to `visibility == "public"` regardless of `filters.visibility`; verify with `tests/test_api_visibility.py`

## 3. FRBR Relation Graph Hardening (C133 Moderate)

- [x] 3.1 Replace per-row `db.session.get()` and lazy ORM loads in `app/core/graph_service.py` with batched/eager queries and push `Item` visibility + `.limit()` bounds into SQL in `_expand_manifestation`; verify query count and results in `tests/test_catalog_graph_api.py`
- [x] 3.2 Add `@limiter.limit("60 per minute")` to `GET /api/catalog/graph` in `app/api/works.py` and URL-encode `contributor.name` via `urllib.parse.quote_plus` in `app/core/graph_service.py`; verify encoded URLs (`&`, `+`) and rate-limit decorator in `tests/test_catalog_graph_api.py`

## 4. Vision SSRF, Upload Safety, Serial Gating & Timeout Alignment (C135 Moderate)

- [x] 4.1 Validate `OLLAMA_URL` (`http`/`https` schemes, strip credentials, block `169.254.0.0/16` & `fe80::/10`) in `app/api/admin.py` and `app/utils/vision.py`, and prevent `_resolve_ollama_base_url()` from probing `localhost:11434/api/tags` when `probe_ollama=False`; verify with `tests/test_admin_api.py` and `tests/test_vision.py`
- [x] 4.2 Catch `Image.DecompressionBombError` in `upload_cover` (`app/api/manifestations.py`) returning HTTP `400`, and remove per-request global `Image.MAX_IMAGE_PIXELS` mutations from `app/api/scanner.py` and `app/utils/vision.py`; verify with `tests/test_images.py` and `tests/test_vision.py`
- [x] 4.3 Gate `_enrich_llm_serial_result()` and cover-issue heuristics in `app/utils/vision.py` behind explicit serial cues so plain book scans skip 8-pass Tesseract OCR and avoid magazine misclassification, and align `_extract_via_ollama` timeout with the frontend polling budget; verify book + all 6 *National Geographic Polska* fixtures in `tests/test_vision.py`

## 5. Atomic Manual Serial Ingest & `/scan` SSR Hydration (C132 Moderate)

- [x] 5.1 Add `commit: bool = True` to `IngestService.ingest_serial_from_meta()` (`app/core/ingest.py`), pass `commit=False` from `add_item_manual()` (`app/api/items.py`) so failed `Item` creation rolls back cleanly, and add serial numeric range bounds (`publication_month` 1–12, `publication_year` 1400–2100, `cumulative_issue_number >= 1`) to `ItemManualCreateSchema` (`app/api/schemas.py`); verify with `tests/test_serial_scan_disambiguation.py`
- [x] 5.2 Move `window.location.search` reads in `frontend/app/scan/page.tsx` out of `useState` initializers into `useEffect` (or `useSearchParams()` inside `<Suspense>`) to eliminate SSR hydration mismatches; verify with `frontend/__tests__/app/scan/page.test.tsx`

## 6. Verification & Pre-Tag Gate

- [x] 6.1 Run `IQOQO_AI_MODE=1 make secret-scan && IQOQO_AI_MODE=1 make lint && IQOQO_AI_MODE=1 make test-parallel` and verify all 4 streams pass cleanly before updating `docs/CHANGELOG.md` and pushing to `release/1.1.0`
