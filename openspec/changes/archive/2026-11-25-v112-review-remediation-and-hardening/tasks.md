## 1. FRBR Merge & ETL Collision Integrity (Critical #2 & #3)

- [x] 1.1 Write failing regression tests in `tests/test_frbr_merge_coverage.py` (or `tests/test_cross_media_work_linking.py`) reproducing reversed-pair `WorkLinkCandidate` (`(S, C)` + `(C, T)`) `IntegrityError` during `merge_works(S, T)` and third-party `WorkRelation` + `WorkLinkCandidate` collisions during `scripts/etl/merge.py:apply_work_merge_plan()`.
- [x] 1.2 Update `app/core/frbr_merge.py` (`merge_works`) to pre-prune any `WorkLinkCandidate` row touching `source_id` whose peer `Work` `C` already shares an unordered candidate with `target_id` (`(target_id, C)` or `(C, target_id)`) before `REFPOINTS_BY_TIER["work"]` repointing.
- [x] 1.3 Update `scripts/etl/merge.py` (`apply_work_merge_plan`) to delete colliding third-party `catalog.work_relations` triples and unordered `catalog.work_link_candidates` peer pairs on `:source` before executing raw SQL `UPDATE` statements, then run `make format-python` and verify tests pass.

## 2. Cross-Media Engine Hardening & Custodian Reviewer UI (Critical #1, Moderate #1–#4, Low #5–#6)

- [x] 2.1 Write backend regression tests in `tests/test_cross_media_work_linking.py` covering `ConfigService` + `ALLOW_LLM=false` bypass, `allow_redirects=False`, sync wall-clock budget cap, `"text"`/`"audiobook"` `_MEDIA_DERIVATION_RANK` orientation, atomic single-commit `accept_candidate()` with swapped `{source_work_id, target_work_id}` validation (`400` on arbitrary IDs), and `409` rejection when re-accepting non-`pending` candidates.
- [x] 2.2 Update `app/core/work_linking_service.py` and `app/api/admin.py` to route `OLLAMA_URL` (with Docker `host.docker.internal` fallback) and `OLLAMA_DEDUPE_MODEL` via `ConfigService`, honor `ALLOW_LLM`, pass `allow_redirects=False`, enforce bounded sync scan LLM caps (`max_llm_calls <= 5`, `max_llm_seconds <= 12.0`), add `"text"`/`"audiobook"` to `_MEDIA_DERIVATION_RANK`, and make `accept_candidate()` single-commit atomic with `409` status & pair-override validation.
- [x] 2.3 Update `Makefile` (`reconcile-cross-media` target) to support `USE_DOCKER=true` via `$(DOCKER_EXEC_WEB)` alongside host `.venv/bin/python`.
- [x] 2.4 Update `frontend/components/admin/work-link-reviewer.tsx` (and `frontend/messages/{en,pl}.json` if new swap/cancel keys are needed) to replace imperative `searchWorks` (`res.data?.results` bug) with `useDebounce` + `useCatalogGraphSearch(..., "work", 8)`, render `"—"` for `null` `cand.confidence`, add a Source/Target swap button, and add `<AlertDialogCancel>` to the delete dialog; update `frontend/__tests__/app/admin/work-links/page.test.tsx`.

## 3. Visual Graph Library Mode & Balanced Root Search (Moderate #5, Low #4)

- [x] 3.1 Write regression tests in `tests/test_catalog_graph_api.py` and `tests/test_graph_and_wishlist_services.py` verifying `"derivatives"` `WorkRelation` edges in `GET /api/catalog/graph?mode=library`, balanced per-type quotas + `series` deduplication + `person`-only `Contributor` filtering in `GET /api/catalog/graph/search`, bounded `_expand_work()` `WorkRelation` queries, and `q` length (`<= 200`) handling.
- [x] 3.2 Update `app/core/graph_service.py` (`build_library_graph`, `search_root_candidates`, `_expand_work`) and `app/api/works.py` (`search_catalog_graph_roots`) to implement `"derivatives"` library edges, fair per-type quotas with overflow backfill, `series` ID deduplication, `Contributor.type == "person"` filtering, `.limit(MAX_GRAPH_NODES)` on `_expand_work()` `WorkRelation` queries, and `q <= 200` length capping.

## 4. Mixed-Media Manifestation FTS, Work Facets & Offline Collection (Moderate #6 & #7, Low #2)

- [x] 4.1 Write backend regression tests in `tests/test_search.py` and `tests/test_api_facets.py` reproducing `_pg_manifestation_fts()` `cd_dvd_combo` matching under `category="movie"` and multi-expression `Work` secondary category deduplication in `DataManager.get_faceted_stats(..., target_entity="works")`.
- [x] 4.2 Update `app/core/search_service.py` (`_pg_manifestation_fts`) to apply the `MIXED_MEDIA_FORMAT_CATEGORIES` SQL `OR` clause and update `app/core/data_manager.py` (`get_faceted_stats`) to exclude `Work.id` rows already counted in the primary category aggregate when adding secondary mixed-media counts.
- [x] 4.3 Update `frontend/app/collection/page.tsx` (`effectiveOffline` memo) to filter cached items by `expressionKindFilters` (defaulting missing `expression_kind` to `"studio"`) and `cd_dvd_combo` mixed categories, resolving the `react-hooks/exhaustive-deps` ESLint warning, and add Vitest coverage.

## 5. LOD RBAC, Cover Upload Fallback, Ontology & Documentation Polish (Moderate #8, Low #1, #3, #7–#9)

- [x] 5.1 Update `frontend/components/manifestation/semantic-links.tsx` to gate `scanButton` on `canEdit` in both compact and full modes, update `frontend/components/item/item-sidebar.tsx` (and verify `/work/[id]` & `/manifestation/[id]`) to pass `canEdit={hasEditPermission}` (`PermissionName.WRITE_METADATA`), localize residual `"Help Request:"`/`"Requests"` strings in `frontend/components/item/item-actions.tsx` (`en.json` / sentence-case `pl.json`), and update Vitest specs (`semantic-links`, `item-sidebar`, `item-actions`).
- [x] 5.2 Update `app/api/manifestations.py` (`upload_cover` synchronous Redis-down fallback) to pass `llm_permissions={}` to `process_tier1_task` and cover with a unit test in `tests/test_covers.py` or `tests/test_api_covers.py`.
- [x] 5.3 Remove `rdfs:subPropertyOf frbroo:R2_is_derivative_of` from `iqoqo:sourceWork` in `docs/ontology/iqoqo.ttl` and verify `python scripts/sync_ontology.py --check` and `tests/test_ontology_sync.py` pass with zero OWL domain clash.
- [x] 5.4 Align the Playwright test title in `frontend/__tests__/e2e/faceted_catalog_sync.spec.ts`, update `docs/images/blueprints/blueprint-8-graph-explorer.svg` (`6` -> `7` edge categories), and update `docs/CHANGELOG.md` (`[1.1.2]` `"Replace Cover"` fix, `run.sh --stop` safety, and `C152` hardening summary).

## 6. Formatting, Lint, Meta-Test & Full Verification Gates

- [x] 6.1 Run `IQOQO_AI_MODE=1 make format-python && IQOQO_AI_MODE=1 make format-js` across all modified Python and TypeScript/JSON files.
- [x] 6.2 Run `IQOQO_AI_MODE=1 make secret-scan && IQOQO_AI_MODE=1 make lint` and confirm zero secret findings, zero lint errors, and zero `collection/page.tsx` hook warnings.
- [x] 6.3 Run targeted Pytest (including PostgreSQL merge/FTS tests if available + ontology/OpenAPI/type-gate meta-tests), Vitest, and Playwright suites (`IQOQO_AI_MODE=1 make test-fast`), then sync/archive `C152`, commit, push to `origin/release/1.1.2`, and run `IQOQO_AI_MODE=1 make knowledge-sync`.
