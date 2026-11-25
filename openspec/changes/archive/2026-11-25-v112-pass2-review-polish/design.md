## Context

`C152` (`v112-review-remediation-and-hardening`, archived at `2026-11-25-v112-review-remediation-and-hardening`) resolved all 3 Critical and 8 Moderate Pass-1 review findings on `release/1.1.2` with 13/13 CI checks passing (`5afafa80`). Pass-2 Principal review (`.context/notes/review/1.1.2/principal-review-release-1.1.2-pass-2.md`) identified 3 minor Low-severity polish items tracked cleanly here in `C153` (`v112-pass2-review-polish`) to keep archived `C152` immutable.

## Goals / Non-Goals

**Goals:**
- Prevent synchronous LLM cover fallback inside `POST /api/manifestations/<id>/cover/upload` during Valkey/Celery outages (`llm_permissions={}`).
- Make `series`/`work` deduplication in `GraphService.search_root_candidates()` invariant to `types` query parameter order.
- Synchronize Blueprint 8 SVG labels (`6` -> `7` cross-schema edge categories) in both `docs/images/architecture/` and `frontend/public/images/help/`.

**Non-Goals:**
- Database schema changes, API envelope changes, or frontend component refactors.

## Decisions

1. **`app/api/manifestations.py:981`:** Pass `llm_permissions={}` directly into the synchronous `process_cover_pipeline(...)` fallback call while keeping `llm_permissions=llm_permissions` on the asynchronous `start_cover_processing(...)` call above it.
2. **`app/core/graph_service.py:search_root_candidates()`:** When both `"work"` and `"series"` are present in `requested`, evaluate `"series"` before `"work"` when populating `buckets` (or post-filter `buckets["work"]` against `seen_series_work_ids` after the collection loop) while preserving the caller's original `requested` order when assembling `results` via per-type quotas. Post-filtering `buckets["work"] = [row for row in buckets["work"] if row["entity_id"] not in seen_series_work_ids]` after the collection loop is 2 lines, zero extra SQL queries, and preserves caller ordering!
3. **Blueprint 8 SVG (`08-frbr-visual-relation-graph.svg`):** Update `6 Cross-Schema Edge Categories`, `6 Edge Categories`, `any of 6 edge types`, and `6 Edge` labels to `7` across `docs/images/architecture/08-frbr-visual-relation-graph.svg` and `frontend/public/images/help/08-frbr-visual-relation-graph.svg`.

4. **`scripts/iqopretest.sh` (`wait_for_preview_backend`):** Reuse the 45s `/api/health` readiness loop (checking ports `5000`, `5001`, `8000`, `5002`) both at initial startup and immediately after `make preview-reconcile` (`--force-recreate --no-deps web worker frontend`) so `make status preview` never races against Gunicorn startup.
5. **`app/utils/allegro.py` (`load_allegro_token`):** Query `InstanceSettings.get_value("ALLEGRO_TOKEN_DATA")` first and sync `cache.set(...)`, falling back to `cache.get("allegro_token_data")` only when DB returns `None` or errors. This eliminates stale per-process `SimpleCache` `refresh_failed` state across multi-worker Gunicorn/Celery setups.
6. **`app/utils/isbn.py` (`_lookup_bn_primo_outcome`):** When `data.bn.org.pl/api/bibs.json` returns `bibs: []`, query the public `katalogi.bn.org.pl/primaws/rest/pub/pnxs` endpoint (`q=isbn,exact,{isbn}`) and normalize `pnx.display` fields into the canonical `Biblioteka Narodowa` metadata payload without emitting duplicate telemetry events.

## Risks / Trade-offs

- **None:** All three changes are surgical, backwards-compatible, and zero-migration.

## Migration Plan

1. Implement all 3 fixes + targeted Pytest regression tests on `release/1.1.2`.
2. Run `make format-python`, `make secret-scan`, `make lint`, and targeted Pytest suites.
3. Archive `C153`, commit, push to `origin/release/1.1.2`, and run `make knowledge-sync`.
