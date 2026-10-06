---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

The v0.7.11 release cycle delivered 17 features across faceted navigation, cross-FRBR filtering, format normalization, metadata tooling, wishlist management, auth hardening, and entity lifecycle tracking. While each feature shipped with targeted tests, significant gaps remain across all 4 test layers (backend, frontend, E2E, scripts). These gaps create regression risk as the codebase grows and leave critical paths unverified. This change systematically closes those gaps with additive tests that validate existing behavior without modifying production code.

## What Changes

- **Backend tests (pytest)**: Add unit/integration tests for entity-audit logging (merge, metadata edit), item-custody event appending, cross-FRBR filtering edge cases (3+ simultaneous filters, AND logic), metadata-refetch CLI behavior, and format-mapping CLI apply mode.
- **Frontend tests (Vitest)**: Add component/unit tests for facet ARIA live region announcements, facet URL parameter serialization/deserialization, active filter strip rendering, mobile facet drawer on mobile viewport, wishlist tagging, shared collection UI for unauthenticated users, and item-custody loan button visibility.
- **E2E tests (Playwright)**: Add browser-level tests for cross-FRBR filtering at Works/Expressions level, facet URL sync (shared URL restoring filter state), mobile facet drawer behavior, entity audit log visibility, item custody loan request button visibility, unauthenticated shared collection navigation, ARIA live region announcements, metadata refetch dry-run verification, and facet search-within functionality.
- **Script tests (BATS)**: Add BATS test files for `scripts/fix_physical_kinds.py` (audit, interactive, apply modes), `scripts/refetch_metadata.py` (gap detection, rate limiting, dry-run, force flag), `format_mappings.yaml` validation, and corresponding Makefile target tests.

## Capabilities

### New Capabilities

- `backend-test-coverage`: Pytest unit/integration tests covering entity-audit logging, item-custody events, cross-FRBR filtering edge cases, metadata-refetch CLI, and format-mapping CLI apply mode.
- `frontend-test-coverage`: Vitest component/unit tests covering facet a11y live region, facet URL sync, active filter strip, mobile facet drawer, wishlist tagging, shared collection UI, and loan button visibility.
- `e2e-test-coverage`: Playwright E2E tests covering cross-FRBR filtering at WEM level, facet URL sync restore, mobile drawer, ARIA live region, audit/custody visibility, unauthenticated shared collection, and metadata refetch verification.
- `script-test-coverage`: BATS tests for fix_physical_kinds.py, refetch_metadata.py, format_mappings.yaml validation, and Makefile target verification.

### Modified Capabilities

None. All changes are additive test files. No production spec-level behavior changes. Existing test files may gain additional test cases but their existing test contract remains intact.

## Impact

- **Affected files**: New test files in `tests/backend/`, `tests/unit/`, `tests/e2e/`, and `tests/scripts/`. No production code modified.
- **Test frameworks**: pytest (93+ files extended/created), Vitest (62+ files extended), Playwright (29+ spec files extended), BATS (13+ files extended + new files).
- **CI integration**: New test files automatically discovered by existing test runners (pytest, vitest, playwright, bats). No CI config changes required.
- **Regression surface**: Zero risk to v0.7.11 features. Tests are purely additive and verify existing behavior only.
