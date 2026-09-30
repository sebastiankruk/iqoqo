## Why

Version 0.7.12 introduced major features across escalation, scanner, permissions, dashboard insights, scripts, and UX -- totalling 114 changed files with ~6,992 new lines. A systematic audit of the existing 233 test files against all 0.7.12 changelog items revealed critical coverage gaps: two scanner components (555 lines) have zero tests, the escalation status-filter query has zero backend coverage, `write:metadata` API enforcement is untested for non-admin users, and the new `validate_yaml.py` security script has no tests. Without hardening, future releases risk regressions in user-facing workflows (help requests, barcode scanning, dashboard) that have no automated safety net.

## What Changes

- **Backend**: Add ~25 tests for escalation status filtering, invalid status rejection, resolver display name in API responses, resolution status variants (rejected/duplicate), concurrent resolution handling, non-manifestation target types, `resolved_at` timestamp, and escalation note length validation
- **Backend**: Add ~15 tests for `write:metadata` and `read:metadata` permission enforcement on FRBR edit/search endpoints with non-admin users, Alembic migration upgrade/downgrade verification, and FRBR tree endpoint with non-admin custodian access
- **Backend**: Add ~5 tests for fallback cover design elements (28px footer font, separator line, centered footer, CTA absence) via Pillow pixel inspection, and empty-collection velocity/distribution endpoint responses
- **Frontend unit**: Add ~40 tests for escalation components: `ProcessedRequestsSection` rendering (loading/empty/error/data states), resolver display name, clickable target link hrefs, deletion request UI badges, accordion expand/collapse, multi-escalation pre-filtered array prop, and `escalation-utils.tsx` shared utilities (`getTargetHref`, `getAdminTargetHref`, `getTargetLabel`)
- **Frontend unit**: Add ~30 tests for scanner components: `bottom-sheet.tsx` (tab switching, barcode scan loop, manual search, error display), `top-bar.tsx` (format/policy selectors, flash toggle, back-link), and `camera-capture.tsx` (file upload, vision extraction polling, drag-drop, confirmation dialog, inline variant)
- **Frontend unit**: Add ~10 tests for dashboard edge cases: velocity/distribution empty-data states, `CollectionInsights` loading/error states, velocity/distribution charts with empty arrays, navbar "My Help Requests" link with pending badge
- **Frontend unit**: Add ~5 tests for i18n HelpRequests namespace key parity between en.json and pl.json, and translation completeness for all component-visible keys
- **E2E**: Add ~3 new spec files: `escalation_workflow.spec.ts` (submit help request -> view in My Help Requests -> admin resolves -> verify resolution), `scanner_workflow.spec.ts` (full barcode scan -> disambiguation -> success card -> add to library), and `policy_scanning.spec.ts` (switch policy in top-bar -> scan -> verify success card adapts)
- **Scripts**: Add ~10 tests for `validate_yaml.py` (valid/invalid/missing YAML), `sync_version.py` CLI modes (`--bump patch/minor/major`, `--set`, default sync), and `json_extract()` dialect-aware helper (SQLite vs PostgreSQL)
- **Visual regression**: Uncomment and enable Playwright snapshot assertions in `watermark_verification.spec.ts` for LLM-gen corner watermark and placeholder center watermark

## Capabilities

### New Capabilities

- `escalation-test-hardening`: Backend, frontend, and E2E test coverage for the 0.7.12 escalation system: status filter query parameter, processed requests section, resolver display name, navbar help-requests link, shared utilities, accordion/multi-escalation patterns, deletion request UI, and full E2E submit-to-resolve workflow.
- `scanner-test-hardening`: Unit test coverage for the untested `bottom-sheet.tsx` (419 lines) and `top-bar.tsx` (136 lines) scanner components, expanded camera-capture tests (all upload modes, polling, drag-drop), dedicated E2E scanner workflow test, and remaining scanner strategy unit tests (audio/video/puzzle lookup strategies).
- `permissions-test-hardening`: Backend API tests for `write:metadata` and `read:metadata` permission enforcement on FRBR edit and search endpoints with non-admin users, Alembic migration test for escalation permission assignment, and `@require_permission` decorator unit tests.
- `dashboard-insights-test-edge-cases`: Frontend edge-case tests for dashboard components: velocity/distribution empty-data states, `CollectionInsights` loading and error states, and velocity/distribution charts with zero-data arrays.
- `scripts-test-hardening`: Unit and integration tests for new and modified 0.7.12 scripts: `validate_yaml.py`, `sync_version.py` CLI modes, and `refetch_metadata.py` `json_extract()` dialect helper.
- `i18n-help-requests-structural-tests`: Structural validation tests for the new `HelpRequests` i18n namespace: key parity between en.json and pl.json, and no empty-string values.

### Modified Capabilities

- `cover-provenance`: Add Pillow-level pixel inspection test for the 0.7.12 fallback cover redesign (28px footer font, separator line, centered layout, no CTA text) and enable Playwright visual snapshot assertions for watermarked covers.

## Impact

- **Backend tests**: 7 test files modified or created (`test_api_escalations.py`, `test_api_admin.py`, `test_permissions.py`, `test_covers.py`, `test_api_profile_insights.py`, `test_scanner_strategies.py`, new `test_validate_yaml.py`)
- **Frontend unit tests**: 12 test files modified or created (`escalation-queue.test.tsx`, `escalation-trigger.test.tsx`, `my-escalations.test.tsx`, `navbar.test.tsx`, `collection-insights.test.tsx`, `velocity-chart.test.tsx`, `type-distribution-chart.test.tsx`, new `bottom-sheet.test.tsx`, new `top-bar.test.tsx`, `camera-capture.test.tsx`, new `escalation-utils.test.tsx`, new `i18n-help-requests.test.ts`)
- **E2E tests**: 3 new spec files (`escalation_workflow.spec.ts`, `scanner_workflow.spec.ts`, `policy_scanning.spec.ts`), 1 modified (`watermark_verification.spec.ts`)
- **Script tests**: 2 files modified or created (`test_script_utilities.py`, new BATS test)
- **Zero production code changes** -- this is purely test suite hardening. No API, no UI, no database schema, no dependency changes.
- **Estimated total new tests**: ~130-150 across all layers
- **Estimated total new/updated files**: ~25
