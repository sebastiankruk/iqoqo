## Why

The Pass-2 Principal Code Review of `release/1.1.2` (`5afafa80`, `.context/notes/review/1.1.2/principal-review-release-1.1.2-pass-2.md`) confirmed 13/13 green CI checks and zero Critical or Moderate issues, leaving three minor Low-severity polish items. Subsequent live preview verification on `release/1.1.2` uncovered three additional production-readiness fixes folded into `C153`: post-reconcile `web` readiness waiting in `scripts/iqopretest.sh`, DB-authoritative `load_allegro_token()` ordering across multi-worker `SimpleCache` Gunicorn processes, and live Biblioteka Narodowa Primo VE REST fallback when `data.bn.org.pl` lags for new 2026 Alma ISBNs.

## What Changes

- **Safe Synchronous Cover Upload Fallback (`app/api/manifestations.py`):** Pass `llm_permissions={}` to `process_cover_pipeline()` in the synchronous Redis/Valkey-down fallback path of `POST /api/manifestations/<id>/cover/upload` so a corrupted user upload during broker outage never cascades into slow synchronous external/LLM cover generation inside a Gunicorn web worker.
- **Order-Independent Series/Work Deduplication in Graph Root Search (`app/core/graph_service.py`):** Ensure `GraphService.search_root_candidates()` deduplicates `series` `Work` IDs from the `work` bucket regardless of the caller-supplied `types` ordering (e.g., `?types=work,series` as well as `?types=series,work`), so a series `Work` is never emitted twice in a single search response.
- **Blueprint 8 Architecture Diagram Edge Category Parity (`docs/images/architecture/08-frbr-visual-relation-graph.svg`, `frontend/public/images/help/08-frbr-visual-relation-graph.svg`):** Update Blueprint 8 SVG labels and `<desc>` from `6` to `7` cross-schema edge categories to reflect the `"derivatives"` (`WorkRelation`) edge category introduced in `C144`/`C152`.
- **Preview Pretest Post-Reconcile Health Wait (`scripts/iqopretest.sh`):** Extract `wait_for_preview_backend()` (including default port `5000`) and wait for `web` `/api/health` readiness after `make preview-reconcile` recreates containers before running `make status preview`.
- **Multi-Worker DB-First Allegro Token Loading (`app/utils/allegro.py`):** Read authoritative encrypted `InstanceSettings("ALLEGRO_TOKEN_DATA")` from PostgreSQL before falling back to `cache.get("allegro_token_data")`, preventing another Gunicorn worker's stale 24h in-process `SimpleCache` (`refresh_failed: True`) from masking a fresh Device Flow authorization.
- **Live Biblioteka Narodowa Primo VE Fallback (`app/utils/isbn.py`):** Add `_lookup_bn_primo_outcome()` against `https://katalogi.bn.org.pl/primaws/rest/pub/pnxs` when `data.bn.org.pl/api/bibs.json` returns empty `bibs`, resolving brand-new Alma ISBNs (e.g., `9788327170255`) immediately.

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
