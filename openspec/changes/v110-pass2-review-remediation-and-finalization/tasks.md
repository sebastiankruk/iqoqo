## 1. SearchService & Shared Collection Privacy Isolation Fix (CRITICAL)

- [x] 1.1 In `app/core/search_service.py` (`_pg_item_fts` and `_ilike_item_search`), restore `if not filters.include_hidden:` to strictly require `i.is_hidden = FALSE` (`Item.is_hidden.is_(False)`), and when `filters.visibility` includes `"public"`, require `is_hidden = FALSE` on the `"public"` branch so hidden-public rows never leak when `include_hidden=True` is used for `friends_only`.
- [x] 1.2 In `app/api/public_items.py` (`get_shared_collection`, line ~826), pass `include_hidden=include_hidden or any(v != "public" for v in allowed_vis)` to `SearchService.search_items()`, aligning with `fetch_shared_collection_with_cache_policy()`.
- [x] 1.3 Add regression tests in `tests/test_api_public_extended.py` verifying: (a) `SearchService.search_items(q=..., user_id=owner.id, owner_only=True, include_hidden=False)` excludes `private` and `friends_only` (`is_hidden=True`) items; and (b) query-filtered `SharedCollection` links with `visibility_scope="friends_and_public"` and `public_only` + Friend Bonus include matching `friends_only` items while excluding `private` and hidden-public items.

## 2. GraphService Query Bounding & Container Work Batching (LOW)

- [x] 2.1 In `app/core/graph_service.py` (`_expand_expression`), add `.limit(MAX_GRAPH_NODES)` to the `select(Manifestation)` query so serial expressions with large issue counts are bounded in SQL.
- [x] 2.2 In `app/core/graph_service.py` (`_expand_item`), replace per-row `db.session.get(Work, agg.container_work_id)` inside the `reverse_aggs` loop with a single batched `select(Work).where(Work.id.in_(...))` lookup.
- [x] 2.3 Run and verify `tests/test_catalog_graph_api.py`.

## 3. Documentation & Pre-Tag Release Plan Finalization (LOW)

- [x] 3.1 Update `docs/COVERS_SETUP.md` (lines ~123–128) and `docs/API.md` (lines ~640–644) so Vision OCR serial response examples use snake_case keys (`issn`, `indeks`, `issue_number`, `volume`, `publication_year`, `publication_month`, `cover_headline`) matching `app/utils/vision.py:_parse_json_response()`, and document `GET /api/lookup/<barcode>` alongside `GET /api/scanner/preview/<barcode>`.
- [x] 3.2 Stamp `## [1.1.0] - 2026-11-20` in `docs/CHANGELOG.md` and check off completed `v1.1.0` items (`C126`–`C138`) in `.context/notes/plan/1.1.x-release-plan.md`, `.context/notes/iqoqo roadmap.md`, and `.context/notes/iqoqo development notes.md`.
- [x] 3.3 Run `IQOQO_AI_MODE=1 make format-python`, `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and `IQOQO_AI_MODE=1 make test-parallel` to verify all checks pass.
