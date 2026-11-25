## 1. Synchronous Cover Upload Fallback (`app/api/manifestations.py`)

- [x] 1.1 Add a regression test in `tests/test_api_covers.py` (or `tests/test_covers.py`) verifying that when `start_cover_processing()` returns `None`, `POST /api/manifestations/<id>/cover/upload` calls `process_cover_pipeline()` with `llm_permissions={}` even if the uploading user has LLM permissions.
- [x] 1.2 Update `app/api/manifestations.py` (`upload_cover` synchronous fallback) to pass `llm_permissions={}` to `process_cover_pipeline()`.

## 2. Order-Independent Series/Work Deduplication (`app/core/graph_service.py`)

- [x] 2.1 Add a regression test in `tests/test_cross_media_work_linking.py` (or `tests/test_catalog_graph_api.py`) requesting `GET /api/catalog/graph/search?q=...&types=work,series` and asserting a series `Work` appears only once (`entity_type="series"`).
- [x] 2.2 Update `app/core/graph_service.py` (`search_root_candidates`) to filter `seen_series_work_ids` out of `buckets["work"]` after collecting all buckets so deduplication is independent of `types` parameter order.

## 3. Blueprint 8 SVG Parity & Verification Gates

- [x] 3.1 Update `docs/images/architecture/08-frbr-visual-relation-graph.svg` and `frontend/public/images/help/08-frbr-visual-relation-graph.svg` from `6` to `7` cross-schema edge categories (including `"derivatives"`).
- [x] 3.2 Run `IQOQO_AI_MODE=1 make format-python`, `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and targeted Pytest suites, then archive `C153`, commit, push to `origin/release/1.1.2`, and run `IQOQO_AI_MODE=1 make knowledge-sync`.
