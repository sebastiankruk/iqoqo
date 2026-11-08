## Purpose
Provide an interactive pan/zoom/rotate `<MapViewerModal />` for inspecting standalone and attached maps on Book, Game, and Map pages, and allow filtering collections by map presence.

## ADDED Requirements

### Requirement: Interactive Pan/Zoom Map Viewer Modal

Work, Manifestation, and Item detail views with cartographic map attachments SHALL provide a `<MapViewerModal />` supporting zoom (`1x`–`5x`), pan, rotation, and multi-map selection.

#### Scenario: Collector inspects an attached world map on an Item page
- **GIVEN** an Item whose Manifestation has a map attachment (`title="Map of Middle-earth"`)
- **WHEN** the user clicks the map preview or `"Inspect Map"` button
- **THEN** `<MapViewerModal />` opens displaying the high-resolution map with zoom, rotate, and reset controls.

### Requirement: Collection `"Has Map"` Facet Filter

The collection search and facet API (`/api/items`, `/api/stats/facets`) and `sidebar-filters.tsx` SHALL support filtering by `has_map=true`.

#### Scenario: Filtering collection to items with maps
- **GIVEN** a collection containing books with map attachments and books without maps
- **WHEN** the user activates the `"Has Map"` filter facet
- **THEN** only items/manifestations with `has_map` / `hasMapAttachment` (or standalone `cartographic_map` format) are returned.
