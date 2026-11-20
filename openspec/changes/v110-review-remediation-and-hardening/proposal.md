## Why

The Principal + Gemini release review of `release/1.1.0` (PR `#433`, `.context/notes/review/1.1.0/principal-review-release-1.1.0.md`) identified one critical visibility regression and eight moderate security, performance, and reliability defects across `C128`, `C129`, `C132`, `C133`, and `C135`. Resolving all nine findings before tagging `v1.1.0` ensures `friends_only` shared collections actually return friend-scoped items, closes BOLA/SSRF/rate-limit gaps, removes N+1 graph amplification, and prevents book OCR regressions and SSR hydration mismatches.

## What Changes

- **Shared Collection Visibility & Cache Safety (`C129`):** Fix `_build_shared_visibility_predicate()` in `app/api/public_items.py` and `SearchService` `include_hidden` handling so `Item.is_hidden.is_(False)` only constrains `visibility == "public"` and does not drop `friends_only` items (`is_hidden=True`) on `friends_and_public` or Friend Bonus shares. Emit `Vary: Authorization, Cookie` on anonymous `public, max-age=300` share responses too.
- **Bulk Visibility Security & Sync (`C128`):** Remove the 404/403 existence oracle in `PATCH /api/items/bulk-visibility` by filtering owned items uniformly, dispatch ActivityPub/FTS sync on visibility transitions, and pin non-owned `include_public=True` rows in `SearchService` strictly to `visibility == "public"`.
- **FRBR Relation Graph Hardening (`C133`):** Batch-load BFS neighbor queries and push `Item` visibility + `.limit()` bounds into SQL in `app/core/graph_service.py`, add `@limiter.limit("60 per minute")` to `GET /api/catalog/graph` in `app/api/works.py`, and URL-encode `contributor.name` via `urllib.parse.quote_plus`.
- **Vision OCR, Upload & `OLLAMA_URL` Hardening (`C135`):** Validate `OLLAMA_URL` (`http`/`https` schemes, strip embedded credentials, block `169.254.0.0/16` & `fe80::/10`), stop probing `localhost:11434/api/tags` when `probe_ollama=False`, catch `Image.DecompressionBombError` in `upload_cover`, remove racy per-request `Image.MAX_IMAGE_PIXELS` mutations, gate `_enrich_llm_serial_result()` and cover-issue heuristics behind serial cues, and align `_extract_via_ollama` timeout with the frontend poll budget.
- **Atomic Manual Serial Ingest & `/scan` SSR Hydration (`C132`):** Replace mid-transaction `db.session.commit()` in `IngestService.ingest_serial_from_meta()` with `flush()`/`commit=False` when invoked from `add_item_manual()`, add typed numeric range bounds (`publication_month` 1–12, `publication_year` 1400–2100, `cumulative_issue_number >= 1`) to `ItemManualCreateSchema`, and move `window.location.search` reads in `frontend/app/scan/page.tsx` into `useEffect` (or `useSearchParams()` inside `<Suspense>`).

## Capabilities

### New Capabilities

- `v110-review-remediation`: Pre-tag security, visibility, performance, and reliability remediation requirements for `v1.1.0` (`C136`).

### Modified Capabilities

## Impact

- **Backend API & Services:** `app/api/public_items.py`, `app/api/items.py`, `app/core/search_service.py`, `app/core/graph_service.py`, `app/api/works.py`, `app/api/admin.py`, `app/api/manifestations.py`, `app/api/scanner.py`, `app/api/schemas.py`, `app/core/ingest.py`, `app/utils/vision.py`.
- **Frontend:** `frontend/app/scan/page.tsx`.
- **Tests:** `tests/test_api_public_extended.py`, `tests/test_api_visibility.py`, `tests/test_catalog_graph_api.py`, `tests/test_vision.py`, `tests/test_images.py`, `tests/test_serial_scan_disambiguation.py`, `frontend/__tests__/app/scan/page.test.tsx`.
