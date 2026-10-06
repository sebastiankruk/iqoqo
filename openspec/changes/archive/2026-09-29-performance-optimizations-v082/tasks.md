## 1. Shared Filter Builder Extraction

- [x] 1.1 Implement `CatalogFilterBuilder` in `app/api/filters.py` encapsulating format, content-type, tags, collections, genres, publishers, statuses, missing cover/id flags, and ownership filters with join deduplication; verify with unit tests for generated SQL clauses.
- [x] 1.2 Refactor `GET /api/manifestations` in `app/api/manifestations.py` to use `CatalogFilterBuilder` and verify that manifestation filtering tests pass without behavioral differences.
- [x] 1.3 Refactor `app/api/items.py` and `app/core/search_service.py` to consume `CatalogFilterBuilder` and verify existing item listing and search filter tests pass.

## 2. Keyset Cursor Pagination for Manifestations

- [x] 2.1 Implement base64 keyset cursor encoding and decoding utilities in `app/api/manifestations.py` (or `app/utils/pagination.py`); verify with unit tests covering serialization and edge cases.
- [x] 2.2 Update `GET /api/manifestations` to support `cursor` and `limit` parameters returning `next_cursor` and a limit-bound result slice while preserving backward compatibility for `page`/`offset`; verify with multi-page cursor traversal tests.
- [x] 2.3 Add validation and error handling for malformed or out-of-range cursor parameters, verifying HTTP 400 Bad Request responses via API tests.

## 3. Recursive CTE for Hierarchy Traversal

- [x] 3.1 Implement recursive CTE collection ancestor traversal in `app/api/collections.py` using SQLAlchemy `cte(recursive=True)` with recursion depth safety limits; verify with unit tests for multi-level hierarchy resolution.
- [x] 3.2 Update `_validate_parent_hierarchy` to evaluate circular dependencies in a single database query round-trip and verify cycle detection test suite passes.
- [x] 3.3 Verify recursive CTE query compatibility and performance on both SQLite (test environment) and PostgreSQL (production dialect).

## 4. Ownership Facet Query Caching & Optimization

- [x] 4.1 Optimize user ownership filtering in `DataManager._build_item_ids_subq` using set-based pre-filtering to eliminate repeated correlated subqueries; verify with query benchmark tests.
- [x] 4.2 Implement Redis caching for ownership-scoped faceted stats in `DataManager.get_faceted_stats` with normalized query parameter cache keys and TTL limits; verify with caching unit tests.
- [x] 4.3 Add cache invalidation hooks on item creation, deletion, and ownership transfer, verifying through integration tests that modified libraries serve fresh facet counts.

## 5. Memory-Bounded Streaming Catalog Export

- [x] 5.1 Implement chunked batch generator `stream_export_all()` in `app/core/data_manager.py` using SQLAlchemy `yield_per` across Works, Expressions, Manifestations, and Items; verify with tests asserting valid chunked JSON syntax generation.
- [x] 5.2 Refactor `GET /admin/export` in `app/api/system.py` to emit streamed responses via Flask `stream_with_context` and verify that streamed export returns valid JSON matching the full catalog structure.
- [x] 5.3 Implement disconnect cleanup handlers in the streaming generator to guarantee cursor closure upon client connection abortion, verified via simulated disconnect tests.

## 6. REST Idempotency Fix for ISBN Lookup

- [x] 6.1 Refactor `GET /api/isbn/<isbn>` in `app/api/manifestations.py` to be pure read-only, eliminating database inserts and background Celery task dispatches; verify with tests asserting database row counts remain unchanged after GET requests.
- [x] 6.2 Update `POST /item/<isbn>` in `app/api/items.py` and related creation endpoints to explicitly trigger FRBR entity creation and task scheduling, verifying with item creation integration tests.
- [x] 6.3 Verify end-to-end ISBN query and subsequent explicit cataloging workflows through API contract tests.

## 7. Verification & Conformance

- [x] 7.1 Execute full test suite across affected modules (`pytest tests/api/test_manifestations.py tests/api/test_collections.py tests/core/test_data_manager.py tests/api/test_items.py`) and verify 100% pass rate.
- [x] 7.2 Run `openspec validate performance-optimizations-v082 --strict` and verify all change artifacts pass strict schema validation.
