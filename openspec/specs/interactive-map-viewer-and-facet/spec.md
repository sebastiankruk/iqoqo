# interactive-map-viewer-and-facet Specification

## Purpose

Provide an interactive pan/zoom/rotate `<MapViewerModal />` for inspecting standalone and attached maps on Book, Game, and Map pages, and allow filtering collections by map presence.

## Requirements

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

### Requirement: Safe URL Rendering, Delete Attachment Control, Scale/Projection Inputs, and Keyboard Navigation (`C-01`, `M-07`)

`<MapViewerModal />` and `<ExtendedMetadataMaps />` MUST sanitize external URLs before rendering, allow authorized editors to delete attachments and enter scale/projection metadata on upload, and support keyboard navigation in the viewer modal.

#### Scenario: Block non-http(s) and non-relative URLs in `<MapViewerModal />`

- **GIVEN** a map attachment with an unsafe `url` scheme (such as `javascript:` or `data:`)
- **WHEN** `<MapViewerModal />` renders
- **THEN** it MUST NOT bind the unsafe URI to `<img src>` or `<a href>` ("Open Full Image in New Tab").

#### Scenario: Delete map attachment and provide scale/projection during upload in `<ExtendedMetadataMaps />`

- **GIVEN** `<ExtendedMetadataMaps canEdit={true} manifestationId={10} />` with an existing attachment `att-1`
- **WHEN** the user clicks the delete button on `att-1`
- **THEN** the component MUST call `DELETE /api/manifestations/10/map-attachments/att-1` and remove `att-1` from the rendered list
- **AND** the "Add Map Attachment" dialog MUST expose optional `Scale` and `Projection` inputs and disable submission when neither a file nor an image URL is supplied.

#### Scenario: Keyboard navigation in `<MapViewerModal />`

- **GIVEN** `<MapViewerModal open={true} />` with multiple map attachments
- **WHEN** the user presses `+`/`=`, `-`, `r`, `0`, `ArrowLeft`, or `ArrowRight`
- **THEN** the viewer MUST zoom in, zoom out, rotate 90°, reset the view, or navigate between attachments respectively.
