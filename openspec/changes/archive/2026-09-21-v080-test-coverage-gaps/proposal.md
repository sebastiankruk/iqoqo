## Why

Version 0.8.0 introduces major Semantic Web features (SPARQL endpoint, public Linked Data, data export) with excellent backend test coverage (279 dedicated tests), but critical E2E and frontend coverage gaps remain. The data sovereignty export feature lacks E2E validation, SPARQL Explorer has minimal E2E coverage (1 test file), and several high-traffic pages have <60% frontend coverage. These gaps create regression risk for user-facing features that were added in this release.

## What Changes

- Add E2E test suite for data sovereignty export workflow (JSON-LD, Turtle, JSON formats)
- Expand SPARQL Explorer E2E coverage with query editor, result format switching, and error handling tests
- Improve frontend test coverage for low-coverage pages: `app/item/[id]/page.tsx` (45.83% → 70%+), `app/profile/page.tsx` (54.87% → 70%+), `app/scan/page.tsx` (53.46% → 70%+)
- Add migration downgrade tests for `v0_7_19_f3_column_promotion` to validate rollback scenarios
- Add performance/load tests for SPARQL endpoint with large datasets (5000+ items)
- Add i18n completeness tests for new SPARQL Explorer and export UI components
- Fix 10 pre-existing mypy type errors in `app/core/sparql_service.py` (non-blocking but affects type safety)

## Capabilities

### New Capabilities
- `testing/data-export-e2e`: End-to-end test coverage for user data sovereignty export workflow
- `testing/sparql-explorer-e2e`: Comprehensive E2E test coverage for SPARQL query interface
- `testing/frontend-coverage-improvement`: Frontend test coverage improvements for low-coverage pages
- `testing/migration-downgrade`: Migration downgrade and rollback test coverage
- `testing/sparql-performance`: Performance and load testing for SPARQL endpoint
- `testing/i18n-completeness`: Internationalization test coverage for new features
- `testing/type-safety`: Mypy type error resolution for SPARQL service

### Modified Capabilities
(none - all new testing capabilities)

## Impact

- **Test Infrastructure**: New E2E test files in `frontend/__tests__/e2e/`
- **Frontend Coverage**: Test files for `app/item/[id]`, `app/profile`, `app/scan` pages
- **Backend Tests**: Migration downgrade tests in `tests/test_migration.py`
- **Performance Tests**: New load test suite for SPARQL endpoint
- **Type Safety**: Type annotations in `app/core/sparql_service.py`
- **CI/CD**: All new tests must pass in CI pipeline
- **Estimated Effort**: 8-10 hours of test development work
