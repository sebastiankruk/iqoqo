---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

After releasing v0.7.10, user testing revealed that the faceted navigation sidebar is **erratic and untrustworthy**: filters apply inconsistently (single-select-only on some facets, wrong AND/OR logic), genre filtering is entirely broken, empty facets remain visible, FRBR terminology is exposed raw to end-users, and facet counts don't reflect the actual records rendered. Collectors cannot reliably browse their library. This must be fixed before any further feature development builds on top of the navigation layer.

## What Changes

- **Fix AND/OR cross-filtering logic:** Inter-facet = AND, intra-facet = OR, applied uniformly across every facet type (Genre, Physical Kind, Progress, Publishers, Media Category, Collection Status).
- **Enable toggle-to-deselect on all facets:** Clicking a selected value deselects it in-place. No more requiring users to visit the filter bar to remove a filter.
- **Enable multi-select on all facets:** Media Categories, Physical Kind, and all other facets must support multi-value OR selection.
- **Hide empty/zero-count facets and values:** If a facet has no options, it is not rendered. If a facet value drops to 0 during cross-filtering, it is hidden (with animated exit).
- **Fix broken Genre filtering backend:** Genre filter queries currently return zero results; backend join/filter logic must be repaired and covered by tests.
- **Fix FRBR count discrepancies on Media Categories:** Counts must reflect the FRBR level being browsed (Manifestations in global, Items in private), not a hard-coded item count.
- **Abstract FRBR terminology for end-users:** Replace raw schema labels ("Items", "Expressions") with human-friendly copy ("Releases/Editions" in global view, "My Copies" in private library).
- **Add active filter summary strip:** A horizontal scroll area above the grid shows all active filter pills with a single "Clear All" text button.
- **Fix missing translations on Progress facet values:** Add i18n fallback to English for any untranslated Progress enum values; add a lint/test guard to catch future regressions.
- **Handle missing Physical Kind gracefully:** Media categories without a Physical Kind (Movie, Board Game) must not produce broken UI states — either hide the Physical Kind facet for these categories or map to a default generic label.
- **URL state synchronization:** Bind all active facet selections to URL search params to enable bookmarking, sharing, and browser back/forward navigation.
- **Mobile: Floating Filter pill + Bottom Sheet Drawer:** On mobile viewports, collapse the facet sidebar into a fixed floating pill that opens a Shadcn `<Drawer>` (bottom sheet, swipe-to-dismiss). No "Apply" button — changes are instant.
- **High-density facet: search-within-facet input:** For facet groups exceeding 10 options (e.g., Publishers, User Tags), add a borderless inline search input to cull the list.
- **Accessibility — aria-live announcements:** When a filter is toggled, an invisible `aria-live="polite"` region announces the resulting count to screen readers.
- **Animated layout stability (CLS prevention):** Use `framer-motion` `layout` prop on facet containers so that disappearing values slide out smoothly rather than causing layout jumps.

## Capabilities

### New Capabilities

- `facet-url-sync`: Serialize/deserialize all active facet state to/from URL search parameters to support deep-linking, bookmarking, and browser history navigation.
- `mobile-facet-drawer`: Mobile-viewport facet experience: floating "Filter Library" pill triggers a Shadcn `<Drawer>` bottom sheet containing all facet groups; swipe-to-dismiss, no explicit Apply button.
- `facet-search-within`: Inline search input rendered inside facet groups with > 10 options, allowing users to type to filter the facet value list.
- `active-filter-strip`: Horizontal scroll pill strip displayed above the result grid, showing all active filters with individual dismiss chips and a single "Clear All" text button.
- `facet-a11y-live-region`: ARIA live region announcing filter results to screen readers when facet state changes.

### Modified Capabilities

- `faceted-navigation`: Expand existing spec to cover: uniform AND/OR logic across all facets (not just the originally listed ones), toggle-to-deselect in-place, hiding of zero-count values during cross-filtering, animated exit of disappearing values (CLS prevention), and rendering the active filter summary strip above results. Also adds Genre and Physical Kind to the supported facet keys list.

## Impact

- **Backend (`app/api/`)**:
  - `filters.py` — fix Genre join/filter query; add Publisher and Collection Status queries; ensure all facet count queries respect FRBR level (Manifestation vs Item) based on context (global vs private).
  - `items.py` / `manifestations.py` — ensure facet aggregation endpoints accept and correctly propagate multi-value OR parameters for all facet keys.
- **Frontend (`frontend/`)**:
  - `components/library/facets/` — new `FacetGroup` component (checkbox + animated exit, search-within), `ActiveFilterStrip`, `MobileFacetDrawer`.
  - `app/library/` (page) — wire up URL search params as the single source of truth for filter state; integrate active filter strip; conditionally render sidebar vs mobile drawer.
  - `lib/i18n/` — add/verify Progress enum translation keys; add test guard.
  - `components/ui/` — leverage existing Shadcn `Checkbox`, `Badge`, `Drawer`.
- **Tests**:
  - Backend: pytest for Genre filtering correctness, multi-value OR logic, empty-facet suppression, FRBR-level-aware counts.
  - Frontend: Vitest/RTL for FacetGroup toggle/deselect/multi-select, ActiveFilterStrip, URL param sync.
  - E2E: Playwright for full cross-filtering flow, mobile drawer interaction, bookmark/share URL round-trip.
