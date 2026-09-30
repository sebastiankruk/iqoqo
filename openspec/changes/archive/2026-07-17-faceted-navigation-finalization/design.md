---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

iqoqo's collection browser (`/collection`) already ships a `SidebarFilters` component, a `FilterBar` chip strip, a `MobileFilterDrawer`, and partial URL state synchronization. However, post-0.7.10 user testing surfaced a constellation of bugs that make the navigation experience erratic and untrustworthy:

1. **Broken AND/OR logic**: Category and Physical Kind facets use `<input type="radio">` — forcing single-select and preventing both deselect-in-place and multi-select OR behavior. The `useInfiniteItems` call passes only `categoryFilters[0]` and `formatFilters[0]`, silently ignoring any additional selections.
2. **Genre filtering is broken**: `filters.py:apply_genre_filter` builds the correct query, but the backend `items.py` endpoint never forwards the `genres` query parameter to the Genre JOIN, so all genre selections return 0 results.
3. **FRBR count discrepancy**: Facet counts on Media Categories in global view are computed against `Item` rows (private library scope), not `Manifestation` rows, making counts misleading.
4. **Empty facets visible**: Publishers and Collection Status sections remain rendered even when there are no options. Zero-count values are selectable, confusing users.
5. **Partial URL sync**: `category` and `format` filters are not written to the URL params, so browser back/forward and bookmarks lose those selections.
6. **Progress enum without i18n fallback**: The `progressLabels` map in `sidebar-filters.tsx` provides a hard-coded English label as a JS default but does NOT fall back correctly when a `t()` call finds no key — it uses `{ defaultValue: info.label }` which is only applied if the key is missing from translations, yet unknown enum values (future additions) would show the raw key string.
7. **Missing Physical Kind graceful handling**: Media categories (Movie, Board Game) that have no sub-formats show an empty Physical Kind section.

The existing `MobileFilterDrawer` is a slide-in from the left — it uses an overlay+backdrop pattern, not a Shadcn `Drawer` bottom sheet. There is already a functional `mobile-filter-drawer.tsx`. The mobile experience needs upgrading to a true bottom sheet with swipe-to-dismiss.

The `SearchableFacet` component already exists and activates search at >5 options — the threshold should be raised to 10 per the UX audit.

## Goals / Non-Goals

**Goals:**

- Fix all AND/OR logic: convert category/format from radio to checkbox, pass full arrays to backend hooks, update backend to accept and apply multi-value category/format parameters.
- Fix Genre filtering end-to-end (backend join wiring in `items.py`/`manifestations.py`).
- Correct FRBR-level-aware facet counts (Manifestation scope for global view, Item scope for private).
- Hide empty facets and zero-count values at render time (CSS + conditional render).
- Complete URL state synchronization: add `category` and `format` to URL params; add and read initial values from URL on mount.
- Upgrade mobile filter experience to Shadcn `<Drawer>` bottom sheet (swipe-to-dismiss).
- Add i18n lint guard for Progress enum and add English fallbacks for any untranslated Progress values.
- Add `aria-live="polite"` region for screen reader announcements on filter change.
- Handle missing Physical Kind gracefully (hide section if no formats for category).
- Abstract FRBR terminology in UI copy (global = "Releases", private = "My Copies").
- Raise `SearchableFacet` search threshold from 5 to 10 options.

**Non-Goals:**

- Full Framer Motion animated exit for zero-count values (deferred to a polish pass; CSS opacity/height transition is acceptable for this release).
- Collector analytics, social sharing, or RSS feed (v0.7.12+).
- Celery/Redis async ingestion or federation (v0.9.0+).
- Mobile app (Capacitor) changes (v1.0.0).
- Complete MemPalace OpenSpec indexing (tracked separately in roadmap Dev+Ops section).

## Decisions

### D1: Category/Format multi-select via checkbox + full array passthrough

**Decision**: Replace `<input type="radio">` with `<input type="checkbox">` for the Category and Physical Kind (format) facets in `sidebar-filters.tsx`. Update `useInfiniteItems`, `useInfiniteManifestations`, `useInfiniteWorksShelf`, and `useInfiniteExpressionsShelf` hooks to accept and forward `string[]` for `category` and `format`. Update corresponding backend routes to accept multi-value query parameters and apply `OR` logic within the facet.

**Why over keeping radio**: Radios enforce single-select at the HTML level. The UX spec requires intra-facet OR (select Book OR Vinyl). Switching to checkboxes with an existing `isActive()` guard is minimal-diff and safe. The "click active to deselect" behavior is already present in the toggle handler — the radio model breaks it by preventing `onChange` when already checked.

**Alternative considered**: Keep radio but intercept click to deselect if already selected. Rejected because it fights HTML semantics and still cannot do multi-select.

### D2: Genre backend fix — pass genres array through full request chain

**Decision**: In `app/api/items.py` and `app/api/manifestations.py`, read the `genres` query param (already comma-separated), parse it into a list, and pass it to the relevant filter helper. The `apply_genre_filter` logic in `filters.py` is correct — the bug is that the param is never read from the request.

**Why**: Minimal, targeted fix. No schema changes needed.

### D3: FRBR-level-aware category counts via scope param

**Decision**: The `useFacetStats` hook (and its backend `/api/stats/facets` endpoint) currently returns item-scoped counts. Add a `scope` query param (`global | user`) to the endpoint. In global view (`manifestations` mode), pass `scope=global` so counts are computed against `Manifestation` rows. In private (`items` mode), pass `scope=user` for Item rows. Backend `GROUP BY` aggregation already exists — add a branch on `scope`.

**Alternative considered**: Return both counts in a single response. Rejected as it doubles payload for no gain; the view already knows its scope.

### D4: URL sync completeness — add category/format params

**Decision**: Extend the `useEffect` URL sync in `collection/page.tsx` to also write `category` (comma-separated) and `format` (comma-separated) to the URL. Extend initial filter parsing to read these params on mount. This closes the gap where category/format selections were lost on browser back.

**Why**: The existing URL sync pattern is already in place. Extending it to two more facet types is low-risk.

### D5: Mobile — upgrade to Shadcn `<Drawer>` bottom sheet

**Decision**: Replace the current `MobileFilterDrawer` slide-from-left implementation with a Shadcn `<Drawer>` (vaul-based) that slides up from the bottom. The trigger moves from the mobile hamburger button to a floating pill fixed at the bottom center of the viewport. The "Show Results" button inside the drawer closes it.

**Why**: The left-slide pattern was an intermediate placeholder. The UX audit and the original Gemini design spec (from `0.7.11-ux-analysis.md`) call for a bottom sheet. Shadcn `Drawer` is already a dependency in this project. The vaul library handles swipe-to-dismiss natively.

**Trade-off**: The floating pill sits at `z-50` — if other floating elements exist (e.g., bulk-add toolbar), they may collide. The bulk-add toolbar is conditionally rendered in global manifestations view; the filter pill appears in both views. Ensure z-index stacking is tested.

### D6: Empty facet suppression — conditional render

**Decision**: In `sidebar-filters.tsx`, guard each `<AccordionSection>` with a zero-length check on its data. If a facet has no options AND no active selections of that type, return `null` instead of rendering an empty accordion. This is already partially done for `taxonmomies.collections` — apply the same pattern universally.

**Why**: Simplest possible fix. No animation needed; disappearing facets during cross-filtering is a polish-pass concern.

### D7: Active filter strip — reuse FilterBar, upgrade to always-visible pill row

**Decision**: The existing `FilterBar` component renders chips and a "Clear all" button. Move it above the grid unconditionally (currently gated behind `activeFilters.length > 0`). Add `flex-wrap` horizontal scroll on small viewports. No architectural change needed — just CSS and conditional display.

## Risks / Trade-offs

- **[Risk] Multi-category backend performance** → Multiple category values in a SQL `IN()` clause are efficient with existing GIN indexes. Mitigation: no extra index work needed; existing `GROUP BY` query plan is unaffected.
- **[Risk] URL length** → Long tag/publisher selections could produce long URLs. Mitigation: URL params are comma-joined strings, not repeated keys; practical length is well under browser limits for typical collection sizes.
- **[Risk] Vaul Drawer z-index conflict with BulkAddToolbar** → Mitigation: audit z-index values; assign `z-40` to BulkAddToolbar and `z-50` to Drawer overlay.
- **[Risk] Genre filter backend fix breaks SQLite fallback** → The existing `apply_genre_filter` handles both Postgres and SQLite paths. The fix only ensures the param is _read_ from the request; the query logic is unchanged. Mitigation: test with both dialects in pytest.
- **[Risk] i18n lint guard may flag existing valid keys** → Mitigation: scope the test to the `progress_*` key namespace only; use a known-good list.
- **[Trade-off] No Framer Motion animated exit for 0.7.11** → CSS `transition-all` on `max-height` (already in `AccordionSection`) provides acceptable visual smoothness. Full layout animation deferred.

## Migration Plan

1. Backend changes first (`filters.py`, `items.py`, `manifestations.py`, `stats/facets` endpoint) — no schema migration required.
2. Frontend component changes (sidebar-filters, mobile drawer, filter bar, collection page URL sync) — independently deployable.
3. i18n translation key additions — additive, no existing key changes.
4. Run `make format-python`, `make format-js`, `make lint`, `make test` locally before PR.
5. No database migration. No breaking API changes (all new params are optional with backward-compatible defaults).
6. Rollback: revert frontend PR only; backend changes are purely additive and safe to leave deployed.

## Open Questions

- Should `category` filter deselection (clicking active category) clear subordinate `format` filters automatically? (Current radio behavior implicitly did this; checkbox behavior should be specified.) → **Proposed behavior**: Yes — toggling off the last active category clears format selections as formats are sub-categories.
- Confirm the terminology for global view: "Releases" vs "Editions" — pick one term for consistency across all UI copy.
