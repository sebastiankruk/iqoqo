---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

The v0.7.11 release cycle delivered 17 features across 4 functional clusters: faceted navigation (multi-select facets, URL sync, mobile drawer, ARIA a11y, search-within), cross-FRBR filtering (item-level status/tags on works/expressions), format/metadata tooling (normalizer, mappings, CLI scripts), and entity lifecycle (wishlist management, custody tracking, entity audit, auth hardening). Each feature shipped with targeted tests, but coverage gaps persist across all 4 test layers.

**Current test landscape (4 layers):**

| Layer    | Framework  | Location                          | Count     | Key Gaps                                                                                                                                                                                                          |
| -------- | ---------- | --------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend  | pytest     | `tests/`                          | ~93 files | entity-audit, item-custody unit tests, cross-FRBR edge cases, metadata-refetch CLI, format-mapping CLI apply mode                                                                                                 |
| Frontend | Vitest     | `frontend/__tests__/` (excl. e2e) | ~54 files | facet-ARIA-live-region, facet-URL-sync, active-filter-strip, mobile-facet-drawer, wishlist-tagging, loan-button visibility, shared-collection-UI                                                                  |
| E2E      | Playwright | `frontend/__tests__/e2e/`         | ~29 files | cross-FRBR filtering at works/expressions, URL-sync restore, mobile-drawer behavior, ARIA live-region, audit/custody visibility, unauthenticated shared-collection, metadata-refetch dry-run, facet search-within |
| Scripts  | BATS       | `tests/bash/`                     | ~13 files | fix_physical_kinds.py, refetch_metadata.py, format_mappings.yaml validation, Makefile targets                                                                                                                     |

**Constraint**: All changes must be additive. No production code modified. No existing test behavior altered. Regression suite must continue passing.

**Existing partial coverage**: Some E2E files partially overlap with the gaps (e.g., `faceted_catalog_sync.spec.ts` covers basic facet sync, `require_physical_item_interceptor.spec.ts` covers the interceptor, `wishlist_workflow.spec.ts` covers wishlist basics). New tests extend these files with additional scenarios rather than replacing them.

## Goals / Non-Goals

**Goals:**

- Achieve comprehensive test coverage across all 4 layers for v0.7.11 features
- Verify entity-audit logging (merge events, metadata edit events) at the backend level
- Verify item-custody event appending, WEM record immutability, and loan eligibility rules
- Test cross-FRBR filtering with 3+ simultaneous filters and AND logic combinations
- Verify metadata-refetch CLI: gap detection, rate limiting, dry-run, force flag, upsert logging
- Verify format-mapping CLI: audit, interactive, apply/DML, dry-run modes
- Add Vitest unit tests for facet ARIA live region, URL sync serialization, active filter strip rendering, mobile viewport drawer, wishlist tag display, and loan button visibility
- Add Playwright E2E tests for cross-FRBR filtering at Works/Expressions, URL sync full round-trip, mobile drawer interactions, ARIA announcement verification, audit/custody UI visibility, and unauthenticated shared-collection navigation
- Add BATS tests for both CLI scripts, format_mappings.yaml validation, and Makefile target integration
- Maintain regression parity: all existing tests continue passing
- Follow existing test patterns and conventions for each layer

**Non-Goals:**

- Modifying any production code (including bug fixes discovered during testing)
- Refactoring existing test infrastructure or fixtures
- Adding performance/load tests
- Adding accessibility audit tooling (axe-core, etc.)—only verifying ARIA behavior items already implemented
- Rewriting existing tests to improve coverage style
- Adding tests for features not in the v0.7.11 scope
- Modifying CI/CD pipeline configuration
- Adding test coverage metrics or thresholds

## Decisions

### Decision 1: Test organization follows existing conventions

**Choice**: Place new tests alongside existing related test files rather than creating new test subdirectories.

**Rationale**:

- Backend tests already live flat in `tests/` with feature-specific prefixes (e.g., `test_api_items_lending.py`)
- Frontend unit tests mirror component structure under `frontend/__tests__/components/`
- E2E tests use descriptive filenames under `frontend/__tests__/e2e/`
- BATS tests are in `tests/bash/` with one file per concern

**Alternatives considered**:

- Creating a dedicated `tests/v0_7_11/` directory: Rejected—breaks existing pattern, harder to discover tests by feature.
- Single monolithic test file per layer: Rejected—makes test files too large and hard to maintain.

### Decision 2: Extend existing files rather than creating all-new files where possible

**Choice**: Where an E2E spec or unit test file already exists for a related feature, add new `test()` or `describe()` blocks to that file.

**Rationale**:

- `faceted_catalog_sync.spec.ts` → add URL-sync restore and mobile-drawer scenarios
- `require_physical_item_interceptor.spec.ts` → add custody visibility and loan-button scenarios
- `wishlist_workflow.spec.ts` → add tag-display and auth-gating scenarios
- `public_sharing.spec.ts` → add unauthenticated navigation scenarios
- `test_fix_physical_kinds.py` → add apply-mode and edge-case tests
- `test_format_normalizer.py` → add unknown\_\* placeholder tests

**Alternatives considered**:

- All-new files for every gap: Rejected—would fragment related test scenarios across files, making it harder to understand feature coverage at a glance.

### Decision 3: New files only for untested features

**Choice**: Create new test files only where no existing file covers the feature domain.

**New backend files**:

- `tests/test_entity_audit.py` — entity-audit logging (merge, metadata edit)
- `tests/test_item_custody.py` — custody event appending, WEM immutability, eligibility
- `tests/test_metadata_refetch.py` — CLI script for metadata refetch

**New frontend files**:

- `frontend/__tests__/components/facet-a11y-live-region.test.tsx`
- `frontend/__tests__/components/facet-url-sync.test.tsx`
- `frontend/__tests__/components/active-filter-strip.test.tsx`
- `frontend/__tests__/components/mobile-facet-drawer.test.tsx`

**New BATS files**:

- `tests/bash/fix_physical_kinds.bats`
- `tests/bash/refetch_metadata.bats`
- `tests/bash/format_mappings_validation.bats`
- `tests/bash/makefile_tooling.bats`

### Decision 4: Backend test fixtures strategy

**Choice**: Use existing pytest fixtures (`client`, `auth_headers`, `test_db`) and create minimal new fixtures only for audit/custody event verification.

**Rationale**: The existing fixture infrastructure is mature. New fixtures should only bridge the gap for:

- `audit_log_entries()` — fixture to query audit log table
- `custody_events()` — fixture to query custody event table
- `sample_physical_item()` — fixture to create a borrowable physical item with known attributes

### Decision 5: Frontend test rendering strategy

**Choice**: Use `@testing-library/react` for Vitest component tests with `render()` and mock providers matching existing patterns. Use `page.route()` for API mocking in Playwright.

**Rationale**: Consistent with existing 54 Vitest files and 29 Playwright specs. No new mocking library or pattern needed.

### Decision 6: BATS test isolation

**Choice**: Each BATS test file uses `setup()` and `teardown()` functions, mocking script output rather than running actual CLI operations against real data.

**Rationale**: BATS tests must not modify the developer's environment. Mock stdout/stderr, verify exit codes and output patterns. For Makefile tests, use `make -n` (dry-run) to verify target definitions.

## Risks / Trade-offs

| Risk                                                                                                                                | Mitigation                                                                                                         |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Test flakiness in E2E**: Playwright tests for ARIA live regions and mobile viewport may be timing-sensitive                       | Use `page.waitForSelector()` with explicit selectors and generous timeouts; add retry logic in test setup          |
| **Test maintenance burden**: 15+ new test files increase CI run time and maintenance surface                                        | Tests are focused and minimal—each file tests specific behaviors, not redundant paths. No parameterized explosion. |
| **BATS mock fragility**: BATS tests mocking CLI output may break if script output format changes                                    | Pin output format assertions to stable markers (e.g., "AUDIT MODE", "APPLIED") rather than full string matching    |
| **Cross-FRBR test complexity**: Testing 3+ simultaneous filters with AND logic requires careful test data setup                     | Use parameterized pytest fixtures to generate filter combinations rather than hardcoding every permutation         |
| **Unintended coupling to implementation**: Testing audit log row counts or custody event formats could couple tests to DB internals | Assert on observable behavior (log exists, event recorded, state change) rather than exact row counts              |
