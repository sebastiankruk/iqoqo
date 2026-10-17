## ADDED Requirements

### Requirement: Dual-Source Cover Contribution on Manifestation and Item Surfaces
The manifestation and item action surfaces (`manifestation-actions.tsx` and `sidebar-actions.tsx`) MUST enable users with `upload:cover` permission to contribute or replace manifestation covers by either capturing a photo via camera or selecting an existing image file from device storage, accessible from a single unified UI button that directly opens a source selection modal dialog.

#### Scenario: User selects file upload from contribute cover trigger
- **GIVEN** a user with `upload:cover` permission viewing a manifestation without a cover
- **WHEN** the user activates the "Contribute Cover" button
- **THEN** a source selection modal dialog opens with "Take Photo", "Choose from Gallery", and "Cancel"
- **WHEN** the user chooses "Choose from Gallery"
- **THEN** a native file picker opens filtering image MIME types (`image/jpeg`, `image/png`, `image/webp`)
- **WHEN** an image file is selected
- **THEN** the image is uploaded to the manifestation cover endpoint, optimistic status is set to `processing`, and a success toast is displayed

#### Scenario: User replaces existing cover with confirmation
- **GIVEN** a manifestation that already has an existing `cover_url`
- **WHEN** the user activates "Replace Cover"
- **THEN** a source selection dialog warns that the existing cover will be overwritten and prompts for source selection
- **WHEN** the user selects either camera or gallery file
- **THEN** the new cover image is uploaded and initiates background cover regeneration

### Requirement: Unified Cover Upload Trigger in Manual Entry Form
The manual item entry form (`manual-entry-form.tsx`) MUST present a single "Upload Cover" button under the manual cover upload section rather than twin camera/gallery buttons.

#### Scenario: User opens cover source dialog in manual entry
- **GIVEN** a user filling the manual entry form
- **WHEN** the user clicks "Upload Cover"
- **THEN** a source selection dialog opens with "Take Photo" and "Choose from Photos" options
- **WHEN** the user selects either option
- **THEN** the corresponding camera capture or file input is activated without redundant UI buttons

### Requirement: FRBR Entity Level Binding
Cover uploads contributed via this workflow MUST attach strictly to the Manifestation (F3) entity and update `manifestation.cover_url`.

#### Scenario: Cover attachment does not mutate Work or Item records
- **WHEN** a cover is uploaded via the dual-source picker
- **THEN** only the target Manifestation's `cover_url` and `meta["cover_status"]` are modified
- **THEN** associated Work (F1) entities and physical Item (F5) condition/provenance records remain unaltered
