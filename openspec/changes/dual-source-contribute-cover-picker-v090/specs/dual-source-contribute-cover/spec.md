## ADDED Requirements

### Requirement: Dual-Source Cover Contribution on Manifestation and Item Surfaces
The manifestation and item action surfaces (`manifestation-actions.tsx` and `sidebar-actions.tsx`) MUST enable users with `upload:cover` permission to contribute or replace manifestation covers by either capturing a photo via camera or selecting an existing image file from the device storage, accessible from a single unified UI button.

#### Scenario: User selects file upload from contribute cover trigger
- **GIVEN** a user with `upload:cover` permission viewing a manifestation without a cover
- **WHEN** the user activates the "Contribute Cover" button and selects "Choose from Gallery" (or selects an image file via the integrated file picker)
- **THEN** a native file picker opens filtering image MIME types (`image/jpeg`, `image/png`, `image/webp`)
- **WHEN** an image file is selected
- **THEN** the image is uploaded to the manifestation cover endpoint, optimistic status is set to `processing`, and a success toast is displayed

#### Scenario: User replaces existing cover with confirmation
- **GIVEN** a manifestation that already has an existing `cover_url`
- **WHEN** the user activates "Replace Cover"
- **THEN** a confirmation dialog warns that the existing cover will be overwritten
- **WHEN** the user confirms and selects either camera or photo file
- **THEN** the new cover image is uploaded and initiates background cover regeneration

### Requirement: FRBR Entity Level Binding
Cover uploads contributed via this workflow MUST attach strictly to the Manifestation (F3) entity and update `manifestation.cover_url`.

#### Scenario: Cover attachment does not mutate Work or Item records
- **WHEN** a cover is uploaded via the dual-source picker
- **THEN** only the target Manifestation's `cover_url` and `meta["cover_status"]` are modified
- **THEN** associated Work (F1) entities and physical Item (F5) condition/provenance records remain unaltered
