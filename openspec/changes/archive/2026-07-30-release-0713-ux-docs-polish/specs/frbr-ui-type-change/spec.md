## MODIFIED Requirements

### Requirement: Frontend Type Selector

The system SHALL display a type selection input in the FRBR entity edit form (e.g., Manifestation editor). To prevent cognitive overload, the type selection input MUST use a searchable Combobox component (e.g., Shadcn `Command`) instead of a native `<select>` dropdown, allowing keyboard-first filtering and searchability of type options.

#### Scenario: Editing Manifestation Type

- **WHEN** a user edits a Manifestation in the FRBR UI
- **THEN** the form includes a searchable combobox input to select a different FRBR type (e.g., Movie, Book, Board Game)

## ADDED Requirements

### Requirement: FRBR Level Header Layout

The system SHALL consolidate the FRBR level tabs (Work, Expression, Manifestation, Item) in the `frbr-editor.tsx` header. To comply with the heuristic of maximum 4 buttons per container, the horizontal tabs MUST be replaced with a single `Select` component alongside the close button.

#### Scenario: Changing FRBR levels in the editor

- **WHEN** a user opens the FRBR editor
- **THEN** they see a `Select` dropdown in the header to switch between Work, Expression, Manifestation, and Item views, keeping the header UI minimal
