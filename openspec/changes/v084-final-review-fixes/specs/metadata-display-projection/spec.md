## MODIFIED Requirements

### Requirement: Single Display of Each Metadata Field

The system SHALL render each logical metadata field on the item and manifestation detail pages exactly once, and SHALL recognise a field across every accepted spelling of its key case-insensitively. The accepted spellings SHALL be declared in one place that the display logic reads, rather than duplicated between the set of rendered fields and the set of fields to suppress. Internal keys prefixed with `_` SHALL NOT leak into consumer-facing additional details panels. Categorical attributes (such as categories and mechanics) SHALL maintain interactive clickable filter pivots rather than static badges.

#### Scenario: OCR-sourced record with capitalised keys

- **WHEN** a manifestation carries `Format` (capitalised, as the OCR import path produces) and the detail page is rendered with its "Additional Details" section expanded
- **THEN** the value is shown once under the media format section and does not appear again in the additional details list

#### Scenario: Provider-sourced record with lowercase keys

- **WHEN** a manifestation carries `format` (lowercase, as provider adapters produce)
- **THEN** the value is shown once under the media format section and does not appear in the additional details list

#### Scenario: A field whose every spelling is absent

- **WHEN** a manifestation carries only metadata that the display logic does not render in a dedicated section
- **THEN** the key appears in the additional details list with its own label

#### Scenario: A new accepted spelling is declared

- **WHEN** a spelling is added to the declared vocabulary for an already-rendered field
- **THEN** the field continues to render exactly once, without any separate update to a suppression list

#### Scenario: Category navigation pivot remains clickable

- **WHEN** an item or manifestation detail page displays genre, category, or mechanic tags
- **THEN** each tag remains an interactive navigation pivot linking to collection filtered views.

### Requirement: Server-Derived Display Projection

The item detail API (`GET /api/items/<id>`) and manifestation detail API (`GET /api/manifestations/<id>`) SHALL return a display projection of manifestation metadata, in which the server has already determined which fields the interface renders, in what order, and with what label, so the client does not re-derive that decision. The projection SHALL be additive: the complete raw metadata SHALL continue to be returned unchanged.

#### Scenario: Fetching an item for display

- **WHEN** a client requests item detail via `GET /api/items/<id>`
- **THEN** the response contains both the raw metadata and a display projection derived from it

#### Scenario: Fetching a manifestation for display

- **WHEN** a client requests manifestation detail via `GET /api/manifestations/<id>`
- **THEN** the response contains both the raw metadata and a display projection derived from it, preventing fallback metadata leakage.

#### Scenario: A consumer needs the raw metadata

- **WHEN** the item editor requests item detail
- **THEN** the raw metadata is present and unmodified, so fields can be edited and saved

#### Scenario: Projection derivation fails

- **WHEN** the display projection cannot be derived for a manifestation
- **THEN** the raw metadata is still returned, and the display projection is absent or empty rather than malformed
