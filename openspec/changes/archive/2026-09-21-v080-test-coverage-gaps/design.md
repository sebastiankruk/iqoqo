## Context

Version 0.8.0 has excellent backend test coverage (279 dedicated tests) but lacks E2E validation for user-facing features. The data sovereignty export, SPARQL Explorer, and several high-traffic pages have insufficient test coverage. Additionally, 10 pre-existing mypy type errors in `sparql_service.py` affect type safety. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Add comprehensive E2E tests for data export workflow using Playwright
- Expand SPARQL Explorer E2E coverage with query editor and result handling tests
- Improve frontend test coverage to 70%+ for critical pages (item, profile, scan)
- Add migration downgrade tests for safe rollback procedures
- Add performance/load tests for SPARQL endpoint with large datasets
- Add i18n completeness tests for new features
- Resolve all 10 mypy type errors in `sparql_service.py`

**Non-Goals:**
- Achieve 100% test coverage (diminishing returns)
- Refactor existing passing tests (unless they block new tests)
- Add visual regression tests (separate concern)
- Performance optimization based on load test results (separate change)

## Decisions

### Decision 1: Use Playwright for E2E tests
**Choice:** Playwright over Cypress or Selenium
**Rationale:** Already used in project (`frontend/__tests__/e2e/`), faster execution, better browser support, built-in auto-wait
**Alternatives considered:** Cypress (slower, different API), Selenium (more setup, less modern)

### Decision 2: Frontend coverage target of 70%
**Choice:** 70% statement coverage for critical pages
**Rationale:** Balances thoroughness with maintenance burden; 100% has diminishing returns and increases test fragility
**Alternatives considered:** 80% (higher maintenance), 60% (insufficient coverage)

### Decision 3: Separate performance tests from unit tests
**Choice:** Dedicated performance test suite using pytest-benchmark or custom load testing
**Rationale:** Performance tests have different characteristics (longer runtime, resource-intensive) and should not block CI for unit tests
**Alternatives considered:** Inline performance assertions (slows down unit tests), external load testing tool (more setup)

### Decision 4: Type annotations over type: ignore comments
**Choice:** Proper type annotations and type narrowing over `# type: ignore` comments
**Rationale:** Maintains type safety, provides better IDE support, documents intent
**Alternatives considered:** Type ignore comments (loses type safety), Any types (defeats purpose)

### Decision 5: Migration downgrade tests in existing test file
**Choice:** Add downgrade tests to `tests/test_migration.py` rather than separate file
**Rationale:** Keeps migration tests together, easier to maintain, follows existing pattern
**Alternatives considered:** Separate downgrade test file (more files to manage)

## Risks / Trade-offs

**[Risk] E2E tests are flaky** → Mitigation: Use Playwright's auto-wait, add explicit waits for critical elements, retry failed tests in CI
**[Risk] Performance tests slow down CI** → Mitigation: Run performance tests in separate CI job, not on every PR
**[Risk] Type annotations break runtime behavior** → Mitigation: Type annotations are compile-time only, run full test suite after changes
**[Risk] Migration downgrade tests require complex setup** → Mitigation: Use test fixtures and factory functions to create test data
**[Risk] Frontend tests break on UI changes** → Mitigation: Use data-testid attributes for selectors, avoid brittle CSS selectors
**[Trade-off] 70% coverage target vs 100%** → Accept 70% as pragmatic balance; 100% increases maintenance without proportional benefit
**[Trade-off] Separate performance tests vs inline** → Accept separate suite to keep unit tests fast; performance tests run on schedule
