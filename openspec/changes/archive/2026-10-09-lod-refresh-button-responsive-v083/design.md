## Context

See `proposal.md` for motivation. Currently, `frontend/components/manifestation/semantic-links.tsx` lays out its title and trigger button inside `<CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">`. On mobile viewports or with longer localized titles ("Skanuj zewnętrzne LOD"), the button has fixed spacing that squeezes and clips the button boundary against the card edge. In addition, `SemanticLinks` is mounted only on `manifestation-detail-client.tsx`, so copy owners on `/item/<id>` have no way to view or trigger LOD linking for their item's parent manifestation without clicking away.

## Goals / Non-Goals

**Goals:**
- Make `SemanticLinks` header container wrap cleanly on narrow screens (`flex-col sm:flex-row sm:items-center justify-between gap-3`).
- Prevent button label truncation glitches with robust max-width, ellipsis truncation, and title tooltips.
- Expose `SemanticLinks` within the Item Details view in `frontend/components/item/item-tabs.tsx` for items with an associated manifestation.

**Non-Goals:**
- Creating Item-specific (F4) semantic links (LOD links remain strictly scoped to Work F1 and Manifestation F3).
- Altering the backend LOD reconciliation API or pipeline algorithms.

## Decisions

- **Decision 1: Flexible CardHeader layout with Tailwind responsive classes**
  - *Rationale*: Using `flex-col sm:flex-row sm:items-center justify-between gap-3` ensures mobile viewports place the button below or properly aligned with the card title rather than squeezing into an impossible horizontal row.
  - *Alternatives considered*: Fixed width truncation on the title (hurts readability of description text).

- **Decision 2: Mount `SemanticLinks` in `item-tabs.tsx` Details tab**
  - *Rationale*: The Details tab already contains comprehensive manifestation metadata (extended metadata, series parts). Embedding LOD links here keeps the FRBR holding view enriched without cluttering the main sidebar or requiring a redundant top-level navigation tab.
  - *Alternatives considered*: Creating a dedicated "Linked Data" tab in `TABS` (rejected: adds tab clutter when most items only have 1-3 authority links).

## Risks / Trade-offs

- **[Risk]** Item page has permission checks different from Manifestation page.
  - **Mitigation**: Use `hasPermission(PermissionName.EDIT_MANIFESTATION)` to control `canEdit` prop on `SemanticLinks` when rendered inside `item-tabs.tsx`.
