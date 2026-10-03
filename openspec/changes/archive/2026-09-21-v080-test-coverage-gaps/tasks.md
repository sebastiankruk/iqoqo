## 1. Data Export E2E Tests

- [x] 1.1 Create `frontend/__tests__/e2e/data_export_workflow.spec.ts` with test structure and verify file is created
- [x] 1.2 Add test for export button visibility and permissions, verify test passes for authenticated user
- [x] 1.3 Add test for format selection (JSON-LD, Turtle, JSON), verify all three formats can be selected
- [x] 1.4 Add test for download initiation, verify file download starts with correct format
- [x] 1.5 Add test for visibility permissions (hidden items excluded), verify hidden items not in export
- [x] 1.6 Add test for large collection handling (1000+ items), verify export completes without timeout
- [x] 1.7 Add test for error handling (network error, invalid format), verify error messages displayed
- [x] 1.8 Run all data export E2E tests and verify all pass

## 2. SPARQL Explorer E2E Tests

- [x] 2.1 Expand `frontend/__tests__/e2e/sparql_explorer.spec.ts` with query editor tests, verify tests pass
- [x] 2.2 Add test for result format switching (table, JSON, CSV), verify format changes correctly
- [x] 2.3 Add test for error message display (invalid syntax, timeout, no results), verify errors shown
- [x] 2.4 Add test for query history (if implemented), verify queries saved and loaded
- [x] 2.5 Add test for concurrent query handling, verify multiple queries execute without errors
- [x] 2.6 Add test for query size limits, verify size limit enforced with error message
- [x] 2.7 Run all SPARQL Explorer E2E tests and verify all pass

## 3. Frontend Coverage Improvements

- [x] 3.1 Create `frontend/__tests__/app/item/page.test.tsx` for item page, verify file created
- [x] 3.2 Add tests for item page rendering, missing item handling, and actions display, verify coverage reaches 70%+
- [x] 3.3 Create `frontend/__tests__/app/profile/page.test.tsx` for profile page, verify file created
- [x] 3.4 Add tests for profile page rendering, settings update, and collections display, verify coverage reaches 70%+
- [x] 3.5 Create `frontend/__tests__/app/scan/page.test.tsx` for scan page, verify file created
- [x] 3.6 Add tests for scan page rendering, camera permissions, and scan results, verify coverage reaches 70%+
- [x] 3.7 Run frontend test coverage report and verify all three pages have 70%+ statement coverage

## 4. Migration Downgrade Tests

- [x] 4.1 Add downgrade test to `tests/test_migration.py` for F3 column promotion, verify test file updated
- [x] 4.2 Add test for successful downgrade (data moved back to JSONB), verify test passes
- [x] 4.3 Add test for data integrity preservation during downgrade, verify no data loss
- [x] 4.4 Add test for NULL value handling during downgrade, verify graceful handling
- [x] 4.5 Add test for rollback from backup procedure, verify rollback completes successfully
- [x] 4.6 Add test for downgrade with data conflicts, verify conflict handling strategy
- [x] 4.7 Add test for downgrade performance (10000+ records), verify completes within time limit
- [x] 4.8 Run all migration tests and verify all pass

## 5. SPARQL Performance Tests

- [x] 5.1 Create `tests/test_sparql_performance.py` with test structure, verify file created
- [x] 5.2 Add load test for 5000 items, verify query completes within 10 seconds
- [x] 5.3 Add load test for 10000 items, verify query completes within 30 seconds
- [x] 5.4 Add concurrent query test (10 queries), verify all complete without errors
- [x] 5.5 Add test for concurrent queries exceeding limit, verify graceful handling
- [x] 5.6 Add test for MAX_GRAPH_ITEMS enforcement, verify limit enforced
- [x] 5.7 Add test for MAX_GRAPH_TRIPLES enforcement, verify limit enforced
- [x] 5.8 Add test for timeout enforcement, verify query terminated on timeout
- [x] 5.9 Add test for memory usage under load, verify memory stays within bounds
- [x] 5.10 Run all performance tests and verify all pass

## 6. i18n Completeness Tests

- [x] 6.1 Create `frontend/__tests__/lib/i18n-sparql-explorer.test.ts` for SPARQL Explorer i18n, verify file created
- [x] 6.2 Add test for all UI elements having translations, verify no untranslated strings
- [x] 6.3 Add test for error messages being translated, verify errors in user's locale
- [x] 6.4 Create `frontend/__tests__/lib/i18n-data-export.test.ts` for data export i18n, verify file created
- [x] 6.5 Add test for export UI translations, verify all text translated
- [x] 6.6 Add test for format names translation/localization, verify proper handling
- [x] 6.7 Add test for missing translation detection, verify detection works
- [x] 6.8 Add test for locale switching in SPARQL Explorer, verify UI updates without reload
- [x] 6.9 Add test for locale switching in export UI, verify UI updates without reload
- [x] 6.10 Run all i18n tests and verify all pass

## 7. Type Safety Improvements

- [x] 7.1 Fix bindings type annotation at line 247 in `app/core/sparql_service.py`, verify mypy passes
- [x] 7.2 Fix ResultRow indexing at line 253, verify mypy passes
- [x] 7.3 Fix Process type mismatches at lines 383, 395, 449, verify mypy passes
- [x] 7.4 Fix BNode/Literal assignment to URIRef at lines 493, 497, verify mypy passes
- [x] 7.5 Fix list type mismatch at line 508, verify mypy passes
- [x] 7.6 Fix Mapping.get overload at line 625, verify mypy passes
- [x] 7.7 Fix ResultRow assignment at line 644, verify mypy passes
- [x] 7.8 Run mypy on `app/core/sparql_service.py` and verify zero errors

## 8. Integration and CI

- [x] 8.1 Run full test suite (backend + frontend) and verify all tests pass
- [x] 8.2 Verify CI pipeline configuration includes new test files
- [x] 8.3 Verify coverage thresholds are enforced in CI
- [x] 8.4 Run lint checks (ruff, black, isort, eslint, prettier) and verify all pass
- [x] 8.5 Create summary report of test coverage improvements and verify report generated
