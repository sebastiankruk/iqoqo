## 1. Non-Destructive FRBR Author Repair & Relational Display (`scripts/repair_frbr_authors.py`, `app/api/manifestations.py`, `app/api/admin.py`, `Makefile`)

- [x] 1.1 Refactor `repair_work_authors()` in `scripts/repair_frbr_authors.py` to preserve all existing non-author `WorkContribution` roles (`director`, `designer`, `artist`, `composer`, `translator`, `editor`) and sequences, stop copying Work authors into `Manifestation.meta["authors"]`, skip unrepairable empty-author works so `--dry-run` is idempotent, and commit once per batch outside the inner work loop.
- [x] 1.2 Update `_resolve_manifestation_display_author()` in `app/api/manifestations.py` to check relational `Work.contributions` / `Expression.contributions` when `work.meta["authors"]` is empty and guard `getattr(m, "author", None)`.
- [x] 1.3 Update `POST /api/admin/maintenance/repair-authors` in `app/api/admin.py` to dispatch non-dry-run repairs via `submit_task` and record an `EntityAuditLog` entry; update `Makefile` `repair-authors` to drop `-u root` (running as container `appuser`), prevent unprompted auto-prod mutation on bare `make repair-authors`, and register `repair-authors` in `.PHONY` and `help:`.

## 2. Shared Collection Search, PostgreSQL FTS & Wildcard Escaping (`app/api/public_items.py`, `app/core/search_service.py`)

- [x] 2.1 Add `include_hidden: bool = True` to `ItemSearchFilters` and `SearchService.search_items()` in `app/core/search_service.py`, pushing `AND (:include_hidden = TRUE OR i.is_hidden = FALSE)` into `_pg_item_fts` SQL before `LIMIT :limit`, and pass `include_hidden=False` from `app/api/public_items.py`.
- [x] 2.2 Escape `%`, `_`, and `\` via `escape_ilike_term(q.strip())` with `escape="\\"` inside `SearchService.build_ilike_search_clause()`.
- [x] 2.3 Fix `fetch_shared_collection_by_token()` in `app/api/public_items.py` to normalize `filters["status"]` and `filters["tags"]` to `list[str]` (fixing `TypeError: unhashable type: 'list'` on `_INTENT_LEVEL_STATUSES`), and refactor the `UserWorkIntent` wishlist query to SQLAlchemy 2.0 `select()` with dialect-safe field-scoped `ILike` search instead of unconditional `func.immutable_unaccent` and `_meta_text(Work.meta)`.

## 3. ISBN Resilience, Config Deduplication & OpenAPI 3.1 Contract (`app/utils/isbn.py`, `app/services/sparql/worker.py`, `app/config.py`, `app/api/docs.py`, `.env.example`)

- [x] 3.1 In `app/utils/isbn.py`, cap `_calc_timeout()` connect timeout to `remaining`, add `record_outbound_telemetry("biblioteka_narodowa", ...)` to `_lookup_biblioteka_narodowa_outcome()`, and remove duplicate unreachable lines 778–779.
- [x] 3.2 Narrow exception handling in `app/services/sparql/worker.py`, remove duplicate `FEDERATION_ENABLED` in `app/config.py` and duplicate `ALLOW_LLM` in `.env.example`, and document `NEXT_PUBLIC_INSTANCE_URL` in `.env.example`.
- [x] 3.3 Register accurate `302` redirect responses and `form_post` / JSON `requestBody` schemas for `/api/auth/login/apple`, `/api/auth/callback/apple`, `/api/auth/exchange`, and `/api/admin/maintenance/repair-authors` in `app/api/docs.py`.

## 4. Automated Test Coverage

- [x] 4.1 Expand `tests/test_frbr_author_normalization.py` to verify non-author `WorkContribution` preservation (`director`, `translator`), zero `Manifestation.meta["authors"]` pollution, idempotent `--dry-run`, and relational contributor display fallback.
- [x] 4.2 Expand `tests/test_api_public_extended.py` and search tests to verify multi-status `["want_to_read", "reading"]` shared wishlists on SQLite/PostgreSQL, hidden-item FTS exclusion prior to `LIMIT`, and `%`/`_` wildcard escaping.
- [x] 4.3 Add unit tests in `tests/test_isbn.py`, `tests/test_api_admin.py`, and `tests/test_openapi_contract_completeness.py` covering `_calc_timeout` sub-1.5s budgets, BN telemetry recording, async/audited `repair-authors`, and OpenAPI `302`/requestBody contract accuracy.
