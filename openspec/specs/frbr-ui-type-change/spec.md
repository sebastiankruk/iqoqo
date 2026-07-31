# frbr-ui-type-change Specification

## Purpose

Define FRBR entity editing UI layouts, level selection controls, searchable manifestation type comboboxes, and permission escalation flows.

## Requirements

### Requirement: Frontend Type Selector

The system SHALL display a type selection input in the FRBR entity edit form (e.g., Manifestation editor). To prevent cognitive overload, the type selection input MUST use a searchable Combobox component (e.g., Shadcn `Command`) instead of a native `<select>` dropdown, allowing keyboard-first filtering and searchability of type options.

#### Scenario: Editing Manifestation Type

- **WHEN** a user edits a Manifestation in the FRBR UI
- **THEN** the form includes a searchable combobox input to select a different FRBR type (e.g., Movie, Book, Board Game)

### Requirement: Type Change Request Submission

The system SHALL route type changes made by non-admin users through the User Requests system.

#### Scenario: Submitting Type Change

- **WHEN** a regular user submits a type change for a Manifestation
- **THEN** the system creates a User Request of type `CHANGE_TYPE` and does not immediately update the entity

### Requirement: Custodian Type Change Approval

The system SHALL allow Custodians (admins) to approve and apply type changes via the Custodian UI, and this workflow SHALL be verified by automated End-to-End tests.

#### Scenario: Approving Type Change

- **WHEN** a Custodian approves a `CHANGE_TYPE` User Request
- **THEN** the system updates the underlying FRBR entity's `type` attribute and resolves the request
- **AND** Playwright E2E tests validate that the parent Work and Expression records correctly adapt their types to maintain hierarchy consistency.

### Requirement: FRBR Level Header Layout

The system SHALL consolidate the FRBR level tabs (Work, Expression, Manifestation, Item) in the `frbr-editor.tsx` header. To comply with the heuristic of maximum 4 buttons per container, the horizontal tabs MUST be replaced with a single `Select` component alongside the close button.

#### Scenario: Changing FRBR levels in the editor

- **WHEN** a user opens the FRBR editor
- **THEN** they see a `Select` dropdown in the header to switch between Work, Expression, Manifestation, and Item views, keeping the header UI minimal
