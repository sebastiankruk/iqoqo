# Delta Specification: Interactive Map Viewer and Gallery Filter (`C108c`)

## ADDED Requirements

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
