---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Backend — Genre Filtering Fix

- [x] 1.1 In `app/api/items.py`, read `genres` query param from request, parse comma-separated string into a list, and pass it to `apply_genre_filter` in the items query
- [x] 1.2 In `app/api/manifestations.py`, do the same for the global manifestations query (pass `genres` list to genre filter helper)
- [x] 1.3 Write a `pytest` test verifying that `GET /api/items?genres=Jazz` returns only items whose Work metadata includes "Jazz" genre
- [x] 1.4 Write a `pytest` test verifying that `GET /api/manifestations?genres=Jazz` returns only matching manifestations

## 2. Backend — Multi-value Category and Format Filtering

- [x] 2.1 In `app/api/items.py`, change `category` param parsing to accept comma-separated values (list); apply `OR` condition when multiple categories are provided
- [x] 2.2 In `app/api/items.py`, change `format` param parsing to accept comma-separated values (list); apply `OR` condition when multiple formats are provided
- [x] 2.3 Apply the same multi-value category/format changes to `app/api/manifestations.py`
- [x] 2.4 Write pytest tests: multi-category OR returns union; multi-format OR returns union; cross-facet AND gives intersection
- [x] 2.5 Run `make format-python` after all Python changes

## 3. Backend — FRBR-Level-Aware Facet Counts

- [x] 3.1 In the facet stats backend endpoint (`/api/stats/facets` or equivalent), add a `scope` query param accepting `global` | `user`
- [x] 3.2 When `scope=global`, compute category counts against `Manifestation` rows
- [x] 3.3 When `scope=user`, compute category counts against `Item` rows owned by the authenticated user (existing behavior)
- [x] 3.4 Write pytest test: `GET /api/stats/facets?scope=global` returns Manifestation-scoped counts; `?scope=user` returns Item-scoped counts
- [x] 3.5 Run `make format-python` after backend changes

## 4. Backend — Publisher Facet Data

- [x] 4.1 Confirm the taxonomy endpoint (`/api/taxonomies` or `/api/stats/facets`) returns publisher options with counts
- [x] 4.2 If publisher counts are missing from the facet stats endpoint, add a `GROUP BY` aggregation query for publishers
- [x] 4.3 Write pytest test verifying publisher counts are non-empty when publisher data exists in the library

## 5. Frontend — Fix Category/Format from Radio to Checkbox (Multi-select)

- [x] 5.1 In `frontend/components/collection/sidebar-filters.tsx`, replace `<input type="radio">` with `<input type="checkbox">` for the Media Category facet
- [x] 5.2 In `sidebar-filters.tsx`, replace `<input type="radio">` with `<input type="checkbox">` for the Physical Kind (format) facet
- [x] 5.3 Update the filter toggle handler in `frontend/app/collection/page.tsx`: when toggling category off, also clear all format filters (D1 from design.md — deselecting last active category clears formats)
- [x] 5.4 Update `useInfiniteItems` hook call in `collection/page.tsx` to pass full `categoryFilters` array (not `categoryFilters[0]`) to the backend
- [x] 5.5 Update `useInfiniteManifestations` hook call similarly for multi-category support
- [x] 5.6 Update `useInfiniteWorksShelf` and `useInfiniteExpressionsShelf` hook calls similarly
- [x] 5.7 Update the hook signatures in `frontend/lib/api/hooks.ts` to accept `string[]` for category and format params

## 6. Frontend — URL State Sync for Category and Format

- [x] 6.1 In `collection/page.tsx`, add category and format initial filter parsing from URL params (`?category=music,text` and `?format=vinyl`)
- [x] 6.2 In the `useEffect` URL sync block, add category and format to the serialized URL params
- [x] 6.3 Verify browser back/forward correctly restores category and format selections with a manual smoke test

## 7. Frontend — Pass `scope` to Facet Stats Hook

- [x] 7.1 In `collection/page.tsx`, pass `scope="global"` to `useFacetStats` when `viewMode === "manifestations"`
- [x] 7.2 Pass `scope="user"` when `viewMode === "items"`
- [x] 7.3 Update the `useFacetStats` hook in `hooks.ts` to forward the `scope` param to the backend API

## 8. Frontend — Hide Empty Facets and Zero-Count Values

- [x] 8.1 In `sidebar-filters.tsx`, wrap each `<AccordionSection>` with a guard: do not render if the facet has zero options and no active selections of that type
- [x] 8.2 Guard the Physical Kind section: hide if `validFormats.length === 0`
- [x] 8.3 Guard the Genres section: hide if `taxonomies?.genres` is empty and no genre filter is active
- [x] 8.4 Guard the Publishers section: hide if `taxonomies?.publishers` is empty and no publisher filter is active
- [x] 8.5 Guard Collection Status section: do not render in global view (manifestations/works/expressions modes)
- [x] 8.6 Guard Progress section: already gated — verify it correctly does not render when no category is active or no progress statuses exist
- [x] 8.7 In `SearchableFacet`, filter out options with `count === 0` when the option is not currently selected

## 9. Frontend — Mobile: Upgrade to Shadcn Drawer Bottom Sheet

- [x] 9.1 Replace the current `mobile-filter-drawer.tsx` implementation with a Shadcn `<Drawer>` (vaul-backed) bottom sheet
- [x] 9.2 Add a floating fixed "Filter Library" pill button at the bottom center of the viewport (visible only on `< lg` breakpoints)
- [x] 9.3 The floating pill SHALL display a count badge when filters are active
- [x] 9.4 Wiring: the pill's `onClick` opens the drawer; inside the drawer, include the `SidebarFilters` content and a close button
- [x] 9.5 Ensure the drawer supports swipe-to-dismiss (built into vaul — verify it works on device/emulator)
- [x] 9.6 Audit z-index stacking between the floating pill (`z-50`) and any other fixed elements (bulk-add toolbar); assign appropriate z-index values
- [x] 9.7 Run `make format-js` after all TypeScript changes

## 10. Frontend — Active Filter Strip (FilterBar Upgrade)

- [x] 10.1 In `collection/page.tsx`, ensure `FilterBar` renders unconditionally above the grid (not gated behind `activeFilters.length > 0`)
- [x] 10.2 Update `FilterBar` to display horizontally-scrollable chip layout (`overflow-x-auto whitespace-nowrap`)
- [x] 10.3 Verify "Clear All" button appears only when `activeFilters.length >= 2`
- [x] 10.4 Add translation keys for filter chip labels if not already i18n'd

## 11. Frontend — FRBR Terminology Abstraction

- [x] 11.1 Identify all places in the UI where "Items", "Manifestations", "Expressions", "Works" are displayed as user-facing text in the collection browser
- [x] 11.2 In global view (manifestations mode), replace "Manifestations" / "Items" labels with "Releases" or "Editions" — pick one term and apply consistently
- [x] 11.3 In private view (items mode), ensure user-facing labels say "My Copies" or "My Items" — not "Items" / "Manifestations"
- [x] 11.4 Update i18n translation keys in all locale files for the new terminology

## 12. Frontend — i18n / Translation Guard for Progress

- [x] 12.1 In `sidebar-filters.tsx`, ensure the Progress facet rendering falls back to the English label from `progressLabels` for any key not found in translations (verify `{ defaultValue: info.label }` works correctly for ALL enum variants)
- [x] 12.2 Add all Progress enum values as translation keys to every locale file that is supported (en, pl, etc.)
- [x] 12.3 Write a test (Vitest or a lint script) that asserts every key in `progressLabels` has a corresponding translation entry in the default locale file

## 13. Frontend — SearchableFacet Threshold

- [x] 13.1 In `sidebar-filters.tsx`, change the `SearchableFacet` search-input threshold from `options.length > 5` to `options.length > 10`

## 14. Frontend — ARIA Live Region

- [x] 14.1 Add a visually-hidden `aria-live="polite"` region element to the `collection/page.tsx` layout
- [x] 14.2 When filter state changes (i.e., `activeFilters` or result count changes), update the live region text to announce: "Filtered to [active filters]. N results found."
- [x] 14.3 When all filters are cleared, update the live region to announce: "All filters cleared. N results found."

## 15. Tests — Frontend

- [x] 15.1 Vitest/RTL: test that clicking an active Category checkbox deselects it (toggle-in-place)
- [x] 15.2 Vitest/RTL: test that selecting two Category values renders both as checked
- [x] 15.3 Vitest/RTL: test that `SearchableFacet` shows search input when options > 10, hides it when ≤ 10
- [x] 15.4 Vitest/RTL: test that empty facet sections are not rendered when option list is empty
- [x] 15.5 Vitest/RTL: test `FilterBar` chip renders for active category filter and can be dismissed
- [x] 15.6 Vitest/RTL: test URL param serialization includes category and format when those filters are active

## 16. Tests — E2E (Playwright)

- [x] 16.1 E2E: test full genre cross-filtering flow — select genre, verify results update, deselect, verify all results return
- [x] 16.2 E2E: test multi-category OR — select two categories, verify union of results
- [x] 16.3 E2E: test AND across facets — select category and genre, verify intersection
- [x] 16.4 E2E: test URL round-trip — apply filters, copy URL, open in new tab, verify filters restored
- [x] 16.5 E2E: test mobile drawer opens on small viewport, shows facets, closes on swipe/backdrop

## 17. Quality Gates

- [x] 17.1 Run `make format-python` and verify no diff
- [x] 17.2 Run `make format-js` and verify no diff
- [x] 17.3 Run `make lint` — must pass with zero warnings
- [x] 17.4 Run `make test` — all tests pass
- [x] 17.5 Update `docs/CHANGELOG.md` with 0.7.11 release entry covering all changes
