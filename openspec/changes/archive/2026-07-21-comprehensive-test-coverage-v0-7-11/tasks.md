---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Backend Tests — New Files (pytest)

- [x] 1.1 Create `tests/test_entity_audit.py` with test fixtures for audit log querying and test data setup
- [x] 1.2 Add test in `test_entity_audit.py` verifying audit log entry created on entity merge (assert row exists with merge event type, source/target entity IDs)
- [x] 1.3 Add test in `test_entity_audit.py` verifying audit log entry created on metadata edit (assert row exists with edit event type, changed fields recorded)
- [x] 1.4 Add test in `test_entity_audit.py` verifying audit log and custody log are independent (assert audit entry does NOT appear in custody events table)
- [x] 1.5 Create `tests/test_item_custody.py` with test fixtures for custody event querying and sample borrowable physical item
- [x] 1.6 Add test in `test_item_custody.py` verifying custody events are append-only (assert old events unchanged after new event, row count increases by 1)
- [x] 1.7 Add test in `test_item_custody.py` verifying WEM records remain unmodified during custody operations (assert Work/Expression/Manifestation unchanged after custody event)
- [x] 1.8 Add test in `test_item_custody.py` verifying loan request allowed for borrowable items (assert API accepts loan request, event logged)
- [x] 1.9 Add test in `test_item_custody.py` verifying loan request rejected for non-borrowable items (assert API returns error, no event logged)
- [x] 1.10 Create `tests/test_metadata_refetch.py` with test fixtures for items with varying metadata completeness
- [x] 1.11 Add test in `test_metadata_refetch.py` verifying gap detection identifies items with missing metadata fields
- [x] 1.12 Add test in `test_metadata_refetch.py` verifying rate limiting spaces external API requests (assert time between calls >= configured limit)
- [x] 1.13 Add test in `test_metadata_refetch.py` verifying dry-run mode makes no DB writes (assert no metadata changed after dry-run completes)
- [x] 1.14 Add test in `test_metadata_refetch.py` verifying force flag overrides last-checked skip logic (assert metadata refetched despite recent check timestamp)
- [x] 1.15 Add test in `test_metadata_refetch.py` verifying existing data never overwritten by external source (assert pre-existing field value unchanged after refetch)

## 2. Backend Tests — Extend Existing Files (pytest)

- [x] 2.1 Add test in `tests/test_api_facets.py` (or `tests/test_api_status_filters.py`) verifying 3+ simultaneous cross-FRBR filters from different taxonomies (status + format + tag) with AND logic returns correct Works subset
- [x] 2.2 Add test verifying multiple tag filter AND logic (e.g., tags "horror" AND "classic") returns only Works with items having ALL tags
- [x] 2.3 Add test verifying cross-FRBR filter returns empty results with 200 status when no items match
- [x] 2.4 Add test verifying unauthenticated user receives correct public-only filter counts
- [x] 2.5 Add test verifying comma-joined URL parameter parsing correctly splits and applies multiple filter values from query string
- [x] 2.6 Add test in `tests/test_fix_physical_kinds.py` verifying apply/DML mode updates physical kinds according to format_mappings.yaml
- [x] 2.7 Add test in `tests/test_fix_physical_kinds.py` verifying dry-run mode reports without applying changes
- [x] 2.8 Add test in `tests/test_fix_physical_kinds.py` verifying invalid target kind exits with non-zero code and error message
- [x] 2.9 Add test in `tests/test_fix_physical_kinds.py` verifying empty mappings configuration warns and exits without changes

## 3. Frontend Unit/Component Tests — New Files (Vitest)

- [x] 3.1 Create `frontend/__tests__/components/facet-a11y-live-region.test.tsx` testing presence of `aria-live="polite"` element in facet filter component
- [x] 3.2 Add test in facet-a11y-live-region verifying announcement text updates when a filter is toggled on
- [x] 3.3 Add test in facet-a11y-live-region verifying announcement text updates when all filters are cleared
- [x] 3.4 Add test in facet-a11y-live-region verifying element has sr-only visual hiding class
- [x] 3.5 Create `frontend/__tests__/components/facet-url-sync.test.tsx` testing URL parameter serialization when filter selected (assert query params updated)
- [x] 3.6 Add test in facet-url-sync verifying URL parameter deserialization — page loads with pre-selected filters from URL query params
- [x] 3.7 Add test in facet-url-sync verifying multiple filters serialized as comma-separated values in URL
- [x] 3.8 Add test in facet-url-sync verifying all facet query params removed from URL on clear-all
- [x] 3.9 Create `frontend/__tests__/components/active-filter-strip.test.tsx` testing each active filter displayed as removable chip/badge
- [x] 3.10 Add test in active-filter-strip verifying individual filter removal leaves remaining filters intact
- [x] 3.11 Add test in active-filter-strip verifying filter strip not rendered when no filters are active
- [x] 3.12 Create `frontend/__tests__/components/mobile-facet-drawer.test.tsx` testing drawer renders at mobile viewport (below 768px)
- [x] 3.13 Add test in mobile-facet-drawer verifying drawer toggle opens filter panel and close button/backdrop closes it
- [x] 3.14 Add test in mobile-facet-drawer verifying facet UI renders inline at desktop viewport (above 768px) instead of drawer

## 4. Frontend Unit/Component Tests — Extend Existing Files (Vitest)

- [x] 4.1 Add test in `frontend/__tests__/components/item/item-actions.test.tsx` (or closest wishlist-related file) verifying tags displayed on wishlist item cards
- [x] 4.2 Add test verifying wishlist tag persistence after item state change — tags remain unchanged
- [x] 4.3 Add test verifying tag editing controls hidden for non-owners viewing wishlist items (owner-only controls)
- [x] 4.4 Add test in `frontend/__tests__/components/item/item-actions.test.tsx` (or closest custody-related file) verifying "Request Loan" button visible for authenticated user on borrowable physical item
- [x] 4.5 Add test verifying "Request Loan" button hidden for non-borrowable items
- [x] 4.6 Add test verifying "Request Loan" button hidden for unauthenticated users
- [x] 4.7 Add test verifying "Request Loan" button hidden for wishlist-only items (no physical copy)
- [x] 4.8 Add test in `frontend/__tests__/components/collection/collection-page.test.tsx` (or closest shared-collection file) verifying shared collection renders browseable view for unauthenticated users
- [x] 4.9 Add test verifying auth-gated controls (edit/delete/manage) not rendered for unauthenticated users on shared collection

## 5. E2E Tests — New Playwright Specs

- [x] 5.1 Create `frontend/__tests__/e2e/cross_frbr_filtering.spec.ts` testing Works-level browsing with item status filter applied (assert only Works with matching items shown)
- [x] 5.2 Add test verifying Works-level browsing with item tag filter applied
- [x] 5.3 Add test verifying Expressions-level browsing with physical format filter applied
- [x] 5.4 Add test verifying combined status + format cross-FRBR filters with AND logic at Works level
- [x] 5.5 Add test verifying empty result state when no items match cross-FRBR filters
- [x] 5.6 Create `frontend/__tests__/e2e/facet_url_sync.spec.ts` testing URL updates on filter selection (assert browser URL includes filter param)
- [x] 5.7 Add test verifying browser back button restores previous filter state (apply filter A → apply filter B → press back → filter A state restored)
- [x] 5.8 Add test verifying shared URL with facet query params loads with filters pre-applied
- [x] 5.9 Create `frontend/__tests__/e2e/mobile_facet_drawer.spec.ts` testing drawer opens at mobile viewport (375px) when tapping "Filters" button
- [x] 5.10 Add test verifying filter selection inside mobile drawer applies and reflects in results
- [x] 5.11 Add test verifying mobile drawer closes on backdrop tap
- [x] 5.12 Create `frontend/__tests__/e2e/facet_aria_live_region.spec.ts` testing `aria-live` element contains announcement text after filter applied
- [x] 5.13 Add test verifying `aria-live` element announces filter removal
- [x] 5.14 Add test verifying `aria-live` element announces all filters cleared
- [x] 5.15 Create `frontend/__tests__/e2e/facet_search_within.spec.ts` testing search-within input narrows facet options to matching entries
- [x] 5.16 Add test verifying clearing search-within restores all facet options
- [x] 5.17 Add test verifying search-within works correctly while filters are already selected
- [x] 5.18 Create `frontend/__tests__/e2e/metadata_refetch_verification.spec.ts` testing dry-run reports metadata gaps without modifying database
- [x] 5.19 Add test verifying no metadata values changed in DB after dry-run completes

## 6. E2E Tests — Extend Existing Playwright Specs

- [x] 6.1 Add test in `faceted_catalog_sync.spec.ts` verifying shared URL with facet params restores filter state on another browser/device
- [x] 6.2 Add test in `faceted_catalog_sync.spec.ts` verifying multiple facet groups selected reflect correctly in results and URL
- [x] 6.3 Add test in `wishlist_workflow.spec.ts` verifying "View Wishlist Item" actions shown correctly vs "Add to Wishlist" for non-wishlist items
- [x] 6.4 Add test in `wishlist_workflow.spec.ts` verifying tag persistence — tags remain after navigating away and returning
- [x] 6.5 Add test in `wishlist_workflow.spec.ts` verifying auth-gated action buttons (edit/delete) hidden for non-owners
- [x] 6.6 Add test in `require_physical_item_interceptor.spec.ts` verifying loan button visible for authenticated user on borrowable items
- [x] 6.7 Add test in `require_physical_item_interceptor.spec.ts` verifying no loan button for wishlist-only items
- [x] 6.8 Add test in `require_physical_item_interceptor.spec.ts` verifying @require_physical_item decorator rejects invalid physical item IDs with proper error
- [x] 6.9 Add test in `public_sharing.spec.ts` verifying unauthenticated user can browse shared collection items
- [x] 6.10 Add test in `public_sharing.spec.ts` verifying unauthenticated user redirected to login or prompted for auth on protected actions
- [x] 6.11 Add test in advanced_organization or admin-related spec verifying entity audit log is accessible from admin panel and displays merge/edit events
- [x] 6.12 Add test in lending_workflow or custody-related spec verifying loan request button visibility rules match item borrowability

## 7. Script Tests — New BATS Files

- [x] 7.1 Create `tests/bash/fix_physical_kinds.bats` with setup/teardown and test for script exits successfully in audit mode (assert exit 0, output contains audit report)
- [x] 7.2 Add test in `fix_physical_kinds.bats` verifying interactive mode prompts user for mapping decisions
- [x] 7.3 Add test in `fix_physical_kinds.bats` verifying apply mode updates physical kinds (assert exit 0, output indicates updates applied)
- [x] 7.4 Add test in `fix_physical_kinds.bats` verifying dry-run reports without modifying data (assert output contains change report, exit 0)
- [x] 7.5 Add test in `fix_physical_kinds.bats` verifying invalid target kind exits non-zero with error message
- [x] 7.6 Add test in `fix_physical_kinds.bats` verifying empty mappings prints warning and exits without changes
- [x] 7.7 Create `tests/bash/refetch_metadata.bats` with setup/teardown and test for script detecting metadata gaps (assert output lists items with missing fields)
- [x] 7.8 Add test in `refetch_metadata.bats` verifying rate limiting applied between API requests
- [x] 7.9 Add test in `refetch_metadata.bats` verifying dry-run outputs planned changes without modifying database (assert exit 0, output contains "DRY-RUN" or equivalent)
- [x] 7.10 Add test in `refetch_metadata.bats` verifying force flag overrides skip logic (assert item refetched despite recent check)
- [x] 7.11 Add test in `refetch_metadata.bats` verifying already-checked items skipped without force flag
- [x] 7.12 Add test in `refetch_metadata.bats` verifying existing data not overwritten by external source
- [x] 7.13 Create `tests/bash/format_mappings_validation.bats` testing format_mappings.yaml parses as valid YAML without syntax errors
- [x] 7.14 Add test in `format_mappings_validation.bats` verifying mappings file contains expected source/target structure
- [x] 7.15 Add test in `format_mappings_validation.bats` verifying mappings file is not empty (contains at least one entry)
- [x] 7.16 Create `tests/bash/makefile_tooling.bats` testing `make -n fix-physical-kinds` invokes `scripts/fix_physical_kinds.py` (assert exit 0, script name in output)
- [x] 7.17 Add test in `makefile_tooling.bats` verifying `make -n refetch-metadata` invokes `scripts/refetch_metadata.py` (assert exit 0, script name in output)
- [x] 7.18 Add test in `makefile_tooling.bats` verifying make targets pass flags (e.g., `AUDIT=1`) correctly to scripts

## 8. Regression Verification

- [x] 8.1 Run full pytest suite (`make test-backend` or equivalent) — confirm all 93+ existing tests pass, zero regressions introduced
- [x] 8.2 Run full Vitest suite (`make test-frontend` or equivalent) — confirm all 54+ existing tests pass, zero regressions introduced
- [x] 8.3 Run full Playwright suite (`make test-e2e` or equivalent) — confirm all 29+ existing specs pass, zero regressions introduced
- [x] 8.4 Run full BATS suite (`make test-scripts` or equivalent) — confirm all 13+ existing tests pass, zero regressions introduced
- [x] 8.5 Verify all newly added tests pass on first run (no flaky-first-pass failures)
- [x] 8.6 Run all 4 test suites in sequence to confirm no test ordering or shared-state conflicts
