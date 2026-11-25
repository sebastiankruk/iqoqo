## Context

`release/1.1.2` (`PR #453`, currently at `ec3209a0` with 13/13 CI checks passing) folds seven feature and UX OpenSpecs (`C142`–`C144`, `C148`–`C151`). The consolidated Principal + Neon (`PR #453`) release review (`.context/notes/review/1.1.2/principal-review-release-1.1.2.md`) verified zero open Dependabot alerts and strong architectural alignment, while uncovering 3 Critical regressions, 8 Moderate hardening gaps, and 9 Low polish items that should be closed before tagging `v1.1.2`.

No database DDL changes are needed; the Alembic migration head remains `v1_1_2_cross_media_work_links`.

## Goals / Non-Goals

**Goals:**
- Eliminate all `UniqueViolation` / `IntegrityError` failure modes when merging `Work` entities in both ORM (`app/core/frbr_merge.py`) and raw-SQL ETL (`scripts/etl/merge.py`) paths when unordered `WorkLinkCandidate` or directed `WorkRelation` third-party edges collide.
- Restore Custodian manual cross-media `Work` search and creation on `/admin/work-links` with debounced `useCatalogGraphSearch` queries, null-safe confidence rendering, direction swap, and confirmation cancel controls.
- Enforce `ConfigService`, `ALLOW_LLM`, `allow_redirects=False`, and bounded synchronous HTTP latency (`<= 15s`) for cross-media Ollama tie-breaking, fix `"text"`/`"audiobook"` derivation orientation, and make `accept_candidate()` single-commit atomic with `409` status and pair-override validation.
- Close parity gaps across `GraphService` (`"derivatives"` in `build_library_graph()`, balanced quotas + `series` dedupe + `person` filter in `search_root_candidates()`, bounded `_expand_work()`), PostgreSQL `_pg_manifestation_fts()` (`cd_dvd_combo`), `DataManager` multi-expression `Work` facet counts, Capacitor offline `/collection` filtering, `SemanticLinks` `WRITE_METADATA` RBAC, `iqoqo.ttl` OWL domain purity, and `v1.1.2` documentation.

**Non-Goals:**
- Introducing new Alembic migrations, new database tables, or background Celery task queues for cross-media scanning (a bounded sync cap + CLI batch runner suffices for `v1.1.2`).
- Altering the four-tier FRBR hierarchy (`Work -> Expression -> Manifestation -> Item`) or merging cross-media adaptations into single `Work` rows.

## Decisions

### 1. Pre-Pruning Unordered `WorkLinkCandidate` and Third-Party `WorkRelation` Collisions Before Merge Repointing
- **Decision:**
  - In `app/core/frbr_merge.py` (`merge_works`), query all `WorkLinkCandidate` rows touching `source_id` (`source_work_id == source_id` or `target_work_id == source_id`) and all peer `Work` IDs already linked to `target_id` in either direction (`source_work_id == target_id` or `target_work_id == target_id`). Delete any `source_id` candidate whose peer `C` is either `target_id` or already in `target_peers` (and flush) before iterating `REFPOINTS_BY_TIER["work"]`.
  - In `scripts/etl/merge.py` (`apply_work_merge_plan`), before executing `UPDATE catalog.work_relations` and `UPDATE catalog.work_link_candidates`, issue targeted SQL `DELETE` statements removing:
    1. `work_relations` rows where `source_work_id = :source` and `(target, target_work_id, relation_type)` already exists, or `target_work_id = :source` and `(source_work_id, target, relation_type)` already exists.
    2. `work_link_candidates` rows touching `:source` whose peer `C` (`CASE WHEN source_work_id = :source THEN target_work_id ELSE source_work_id END`) already shares a candidate with `:target` in either direction (`(source_work_id = :target AND target_work_id = C)` OR `(source_work_id = C AND target_work_id = :target)`), plus self-pairs if duplicate rows exist within `:source` (`(S, C)` and `(C, S)` cannot coexist due to the index, so peer check against `:target` is exhaustive).
- **Rationale:** `uq_work_link_candidates_pair` indexes `(LEAST(source_work_id, target_work_id), GREATEST(source_work_id, target_work_id))`. Standard directed `RefPoint(unique_together=...)` only checks exact `(source_work_id, target_work_id)` column tuples and misses reversed `(C, target_id)` rows. Pre-pruning unordered peer collisions handles both PostgreSQL and SQLite cleanly without changing table constraints.

### 2. `ConfigService` + `ALLOW_LLM` Governance, Bounded Sync Ollama Budget, and Single-Commit `accept_candidate()`
- **Decision:**
  - Replace raw `os.environ.get("OLLAMA_URL")` / `os.environ.get("OLLAMA_DEDUPE_MODEL")` in `app/core/work_linking_service.py` with `ConfigService.get(...)` and reuse Docker `host.docker.internal` fallback logic (consistent with `app/utils/vision.py`), verify `_is_llm_enabled()` (`ALLOW_LLM`) before `_probe_ollama_available()`, and pass `allow_redirects=False` on `requests.get`/`requests.post`.
  - Add `max_llm_seconds: float | None = None` to `scan_cross_media_candidates()`. When invoked from synchronous HTTP `POST /api/v1/admin/work-links/scan` (`app/api/admin.py`), clamp `max_llm_calls` to `min(requested, 5)` and set `max_llm_seconds=12.0` (`time.monotonic()` deadline) with per-call timeout `min(timeout, remaining_budget)` so HTTP requests always finish well inside Gunicorn's worker timeout while CLI `scripts/reconcile_cross_media.py` retains its full `max_llm_calls` budget.
  - Add `"text": 1` and `"audiobook": 2` to `_MEDIA_DERIVATION_RANK` alongside existing keys so `shared/taxonomy.yaml` `"text"` works always rank as original source material (`rank 1`) below `"movie"` (`3`), `"music"` (`4`), and `"game"` (`5`).
  - Add `commit: bool = True` to `create_work_relation()`. In `accept_candidate()`, verify `cand.status == WORK_LINK_CANDIDATE_PENDING` (raising a `409` `WorkLinkConflictError` subclass or status-coded `WorkLinkValidationError` mapped to HTTP `409` in `app/api/admin.py`), verify `{src_id, tgt_id} == {cand.source_work_id, cand.target_work_id}` when overrides are supplied, call `create_work_relation(..., commit=False)`, update `cand`, and execute a single `db.session.commit()`.

### 3. Reusing `useCatalogGraphSearch` with `useDebounce` in `WorkLinkReviewer`
- **Decision:** Replace `searchWorks()` and manual `srcResults`/`tgtResults` fetch effects in `frontend/components/admin/work-link-reviewer.tsx` with `useDebounce(manualSourceQuery, 250)` + `useCatalogGraphSearch(debouncedSourceQuery, "work", 8)` (and the same for target). Add a swap button (`ArrowLeftRight`) for manual source/target selection (and swap action on pending candidate review), render `cand.confidence != null ? \`${Math.round(cand.confidence * 100)}%\` : "—"`, and add `<AlertDialogCancel>` to the delete dialog.
- **Rationale:** `useCatalogGraphSearch` (`frontend/lib/api/hooks/catalog.ts:1105`) already unwraps `res.data?.data ?? []`, handles query caching/cancellation via TanStack Query, and enforces minimum query length (`>= 2`).

### 4. Graph `"derivatives"` Parity & Balanced Quota Allocation in `search_root_candidates()`
- **Decision:**
  - In `GraphService.build_library_graph()`, when `"derivatives" in allowed_categories` and `len(present_work_ids) >= 2` and `len(edges_map) < effective_max_edges`, query `WorkRelation` where `source_work_id.in_(present_work_ids)` and `target_work_id.in_(present_work_ids)` limited to `effective_max_edges`, emitting `category="derivatives"` edges.
  - In `GraphService.search_root_candidates()`, compute `per_type_quota = max(1, effective_limit // len(requested))`. Fetch up to `effective_limit` candidates per requested entity type (with SQL `.limit(effective_limit)`), filter `Contributor.type == "person"` (or `Contributor.type.is_(None)`) when `ent_type == "person"`, track `emitted_work_ids` from the `series` bucket so `work` does not re-emit series containers, take up to `per_type_quota` from each bucket in order, and then backfill remaining capacity up to `effective_limit` from any bucket overflow.
  - Add `.limit(MAX_GRAPH_NODES)` to `WorkRelation` queries in `_expand_work()` and clamp/validate `len(q) <= 200` in `app/api/works.py:search_catalog_graph_roots`.

### 5. Search, Facet, Offline Collection, RBAC, and Ontology Fixes
- **Decision:**
  - **`_pg_manifestation_fts()` (`app/core/search_service.py`):** Mirror `_pg_item_fts()`'s `MIXED_MEDIA_FORMAT_CATEGORIES` SQL `OR` clause (`LOWER(TRIM(COALESCE(m.format, ''))) IN :cat_mixed_formats`) when `category` is passed.
  - **`DataManager.get_faceted_stats()` (`app/core/data_manager.py`):** When `target_entity == "works"`, exclude `Work.id` rows that already have an `Expression` with `LOWER(Expression.content_type) == sec_cat` in the `sec_q` subquery (`~Work.id.in_(select(Expression.work_id).where(func.lower(Expression.content_type) == sec_cat))`) before adding `sec_cnt` to `cat_counts[sec_cat]`.
  - **`frontend/app/collection/page.tsx`:** Update the `effectiveOffline` filter block to evaluate `expressionKindFilters` (`const itemKind = item.expression_kind || "studio"`) and `cd_dvd_combo` mixed-category membership (`categoryFilters.includes("music") || categoryFilters.includes("movie")` when `format === "cd_dvd_combo"`), and include `expressionKindFilters` in the `useMemo` dependency array.
  - **`SemanticLinks` & `ItemSidebar`:** Render `{canEdit && scanButton}` in both compact and card branches of `SemanticLinks`, and pass `canEdit={hasEditPermission}` (`PermissionName.WRITE_METADATA`) from `ItemSidebar` (verifying `manifestation-detail-client.tsx` and `work-detail-client.tsx` also gate on `WRITE_METADATA`).
  - **`docs/ontology/iqoqo.ttl`:** Remove `rdfs:subPropertyOf frbroo:R2_is_derivative_of ;` from `iqoqo:sourceWork` (`line 308`) and verify `python scripts/sync_ontology.py --check` + SHACL tests pass.

## Risks / Trade-offs

- **[Risk] Restricting `"Scan External LOD"` to `WRITE_METADATA` hides the button for standard item owners (`role="user"`):** -> **Mitigation:** Backend `POST /api/manifestations/<id>/reconcile` ALREADY enforces `@require_permission(PermissionName.WRITE_METADATA)` and returns `403 Forbidden` to standard owners; hiding the dead button eliminates a guaranteed `403` UX trap and satisfies the Interactive UI Wiring & RBAC alignment rule.
- **[Risk] Bounding synchronous HTTP scan LLM calls (`<= 5` pairs / `<= 12s`) leaves remaining ambiguous pairs heuristic-only during UI clicks:** -> **Mitigation:** Remaining ambiguous pairs are still persisted as `pending` `WorkLinkCandidate` rows (`resolution_source="heuristic"`) for Custodian review, and full-catalog LLM sweeps remain available via `make reconcile-cross-media`.

## Migration Plan

1. Zero database schema or Alembic changes (`v1_1_2_cross_media_work_links` remains single head).
2. Land backend, ETL, frontend, ontology, Makefile, and doc updates on `release/1.1.2`, run full lint/type/unit/meta/E2E gates, sync & archive `C152`, and push to `origin/release/1.1.2`.
