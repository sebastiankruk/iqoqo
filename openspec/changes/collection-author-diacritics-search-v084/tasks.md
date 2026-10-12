## 1. Database Schema & Migration

- [x] 1.1 Create Alembic migration enabling PostgreSQL `unaccent` extension and `immutable_unaccent` wrapper function.
- [x] 1.2 Update PostgreSQL `fts_simple` / `search_vector` definitions on Work and Manifestation models to include unaccented text representations.

## 2. Search Service Enhancements

- [x] 2.1 Update `_ilike_item_search` in `app/core/search_service.py` to join `WorkContribution`, `ExpressionContribution`, and `Agent`, matching query tokens against `Agent.name`.
- [x] 2.2 Update `_pg_item_fts` in `app/core/search_service.py` to parse query with unaccented normalization.
- [x] 2.3 Implement SQLite-compatible Python NFKD normalization in `SearchService` to support in-memory test environments.

## 3. Verification & Regressions

- [x] 3.1 Add unit tests in `tests/test_search.py` verifying author name searches ("Gabriel García Márquez") retrieve matching items.
- [x] 3.2 Add unit tests in `tests/test_search.py` verifying diacritic folding ("milosc" matches "miłość", and "Garcia" matches "García").
- [x] 3.3 Run `pytest tests/test_search.py` and verify all search and filter regression tests pass cleanly.
