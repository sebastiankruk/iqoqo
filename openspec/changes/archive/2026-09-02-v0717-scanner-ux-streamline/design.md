## Context

Scanner flow currently confuses users with "Inventory" vs "Catalog" terminology, and the TopBar lacks translations. See proposal.md for motivation. This design covers the technical approach to improve TopBar UX, full i18n, simplify UI components, and reuse state.

## Goals / Non-Goals

**Goals:**
- Provide unambiguous policy mode selection ("Shelf" vs "Wishlist" vs "Catalog Only") with clear explanatory hints.
- Full localization of TopBar headers, format options, and policies in English and Polish via `next-intl`.
- Eliminate redundant network requests on scan success by reusing metadata.
- Make disambiguation sheet clean and fast on mobile with one-tap candidate selection.

**Non-Goals:**
- Redesign or replace the existing two-circle counter-rotating waiting indicator animation.
- Change backend API schema or endpoints (backend already accepts `"inventory"`, `"wishlist"`, `"catalog"` policy parameters).

## Decisions

**1. Policy Naming & TopBar Localization:**
- Map backend policy values to intuitive UI terms:
  - `"inventory"` -> UI label: "Shelf" (`scanner.topBar.policyShelf`, "Półka" in PL) — adding directly to personal shelf.
  - `"wishlist"` -> UI label: "Wishlist" (`scanner.topBar.policyWishlist`, "Lista życzeń" in PL) — adding to personal wishlist.
  - `"catalog"` -> UI label: "Catalog Only" (`scanner.topBar.policyCatalog`, "Tylko katalog" in PL) — contributing metadata to public catalog without creating an owned item.
- Add descriptive helper text in the TopBar / tooltips indicating the active mode.
- Localize all TopBar labels and format icons via `useTranslations("scanner")`.

**2. State Passing to SuccessCard:**
We pass pre-filled metadata directly as props to `SuccessCard` instead of relying on a separate GET fetch.
*Rationale:* Network refetch is redundant and slows down feedback. Initial scan payload already contains canonical manifestation metadata.

**3. Streamlined Candidate Selection in Disambiguation:**
Keep candidate cards minimal and focused on one-tap selection, with fully localized header and helper strings.
*Rationale:* Reduces mobile tap errors and interaction friction.

**4. Preserved Two-Circle Waiting Indicator:**
Maintain the existing counter-rotating concentric circle spinner across camera capture and bottom sheet search states.

## Risks / Trade-offs

- **Risk:** Stored policy key in localStorage vs backend compatibility. → **Mitigation:** Keep internal key values (`"inventory"`, `"wishlist"`, `"catalog"`) unchanged in code and localStorage; only update user-facing display labels and localized strings.

## Migration Plan

Deploy frontend changes and message dictionary updates (`en.json`, `pl.json`). No backend migrations or schema changes needed.

## Open Questions

None.
