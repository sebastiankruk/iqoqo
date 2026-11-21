## MODIFIED Requirements

### Requirement: Dedicated Full-Screen `/graph` Explorer Page and Entity Entry Buttons
The frontend SHALL provide a dedicated full-screen `/graph` page (reading `?type=<entity_type>&id=<entity_id>&depth=<1|2>` for full `CAPACITOR_BUILD=true` static export compatibility) with interactive pan/zoom/drag, edge-type filtering, node inspection drawer, and `"Explore Graph"` navigation buttons on `/work/[id]`, `/expression/[id]`, `/manifestation/[id]`, and `/item/[id]`.

On `/item/[id]`, for physical items with a positive ID (`item.id > 0`), the `"Explore Graph"` entry link SHALL be rendered using the localized `graph.exploreGraph` key (`"Explore Graph"` / `"Eksploruj graf"`) and positioned prominently above the fold in the top item summary header region (preceding secondary sidebar editors and `ItemTabs` in mobile DOM order) across both mobile (`390x844`) and desktop (`1280x800`) viewports, while remaining omitted for virtual wishlist items (`item.id <= 0`).

#### Scenario: Navigating from an entity detail page to `/graph` and recentering on a connected node

- **GIVEN** a user viewing `/work/[id]` (or `/manifestation/[id]`, `/expression/[id]`, `/item/[id]`)
- **WHEN** the user clicks `"Explore Graph"`
- **THEN** the app MUST navigate to `/graph?type=work&id=<id>`, render the centered interactive graph, allow toggling edge-type filter pills (`FRBR`, `Series`, `Parts/Expansions`, `Contributors`, `Maps`, `LOD`), and allow clicking any node to inspect its summary and recenter or open its entity page.

#### Scenario: Physical item detail page surfaces Explore Graph above the fold on mobile and desktop

- **GIVEN** a user viewing a physical item (`/item/<id>` with `id > 0`) on either a mobile (`390x844`) or desktop (`1280x800`) viewport
- **WHEN** the page renders
- **THEN** the localized `"Explore Graph"` link (`graph.exploreGraph`, pointing to `/graph?type=item&id=<id>`) is visible above the fold without scrolling past sidebar forms or `ItemTabs`
- **AND** when viewing a virtual wishlist item (`id <= 0`), the `"Explore Graph"` link is NOT rendered
