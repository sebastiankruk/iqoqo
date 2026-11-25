## Why

The Pass-2 Principal Code Review of `release/1.1.2` (`5afafa80`, `.context/notes/review/1.1.2/principal-review-release-1.1.2-pass-2.md`) confirmed 13/13 green CI checks and zero Critical or Moderate issues, leaving three minor Low-severity polish items: passing `llm_permissions={}` in `upload_cover()`'s synchronous Valkey-down fallback, making `GraphService.search_root_candidates()` `series`/`work` deduplication order-independent when `?types=work,series` is requested, and updating Blueprint 8 SVG edge-category counts (`6` -> `7`).

## What Changes

- **Safe Synchronous Cover Upload Fallback (`app/api/manifestations.py`):** Pass `llm_permissions={}` to `process_cover_pipeline()` in the synchronous Redis/Valkey-down fallback path of `POST /api/manifestations/<id>/cover/upload` so a corrupted user upload during broker outage never cascades into slow synchronous external/LLM cover generation inside a Gunicorn web worker.
- **Order-Independent Series/Work Deduplication in Graph Root Search (`app/core/graph_service.py`):** Ensure `GraphService.search_root_candidates()` deduplicates `series` `Work` IDs from the `work` bucket regardless of the caller-supplied `types` ordering (e.g., `?types=work,series` as well as `?types=series,work`), so a series `Work` is never emitted twice in a single search response.
- **Blueprint 8 Architecture Diagram Edge Category Parity (`docs/images/architecture/08-frbr-visual-relation-graph.svg`, `frontend/public/images/help/08-frbr-visual-relation-graph.svg`):** Update Blueprint 8 SVG labels and `<desc>` from `6` to `7` cross-schema edge categories to reflect the `"derivatives"` (`WorkRelation`) edge category introduced in `C144`/`C152`.

## Capabilities

### New Capabilities

### Modified Capabilities

- `item-detail-ux-declutter`: Enforce `llm_permissions={}` on `POST /api/manifestations/<id>/cover/upload` synchronous `process_cover_pipeline()` fallback when the Celery/Valkey broker is unavailable.
- `visual-frbr-relation-graph`: Enforce order-independent `series`/`work` deduplication in `GET /api/catalog/graph/search` when both `work` and `series` are requested in any order, and align Blueprint 8 SVG documentation to 7 edge categories.

## Impact

- **Backend:** `app/api/manifestations.py`, `app/core/graph_service.py`.
- **Tests:** `tests/test_api_covers.py` (or `tests/test_covers.py`), `tests/test_cross_media_work_linking.py` (or `tests/test_catalog_graph_api.py`).
- **Docs & Static Assets:** `docs/images/architecture/08-frbr-visual-relation-graph.svg`, `frontend/public/images/help/08-frbr-visual-relation-graph.svg`, `docs/CHANGELOG.md`.
- **Schema & Migrations:** Zero database or Alembic changes.
