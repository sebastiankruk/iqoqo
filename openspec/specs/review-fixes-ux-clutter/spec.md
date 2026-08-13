## ADDED Requirements

### Requirement: InstanceSettings single CTA per domain card
The `InstanceSettings` component SHALL group default setting items under a single unified category `CardWrapper` per domain with a single primary "Save Changes" CTA at the card footer. Secondary integration actions (e.g., "Authorize Allegro") SHALL use `variant="outline"` or `variant="secondary"` styling.

#### Scenario: Settings tab with 5 settings

- **WHEN** a user navigates to a settings tab containing 5 individual setting fields
- **THEN** the fields SHALL be grouped under one card with exactly one primary "Save Changes" button, not 5 separate buttons

### Requirement: FRBR Editor action bar overflow menu
The FRBR metadata editor entity header bars SHALL expose at most 2 visible action buttons (primary "Save Entity" and secondary "Add Child"). Tertiary actions (Escalate to Custodian, Delete Entity) SHALL be consolidated into a Shadcn UI `DropdownMenu` (3-dot overflow menu).

#### Scenario: Entity row with 6 possible actions

- **WHEN** a user views a Work entity row in the FRBR editor
- **THEN** only "Save" and "Add Expression" SHALL be directly visible; remaining actions SHALL be in a 3-dot overflow menu

### Requirement: Camera viewfinder processing overlay
The camera viewfinder in `camera-capture.tsx` SHALL display a high-visibility processing overlay with backdrop blur, animated spinner, and descriptive text when an asynchronous barcode lookup or image capture is in progress.

#### Scenario: Barcode scan initiated

- **WHEN** a user captures a barcode image and the API lookup begins
- **THEN** the viewfinder SHALL immediately show a processing overlay with a spinner and "Matching metadata & artwork..." text
