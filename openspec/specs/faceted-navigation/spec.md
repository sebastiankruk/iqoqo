# OpenSpec Specification: Faceted Navigation and Cross-Filtering

## Purpose

This specification locks in the behavioral requirements, cross-filtering rules, and empty-state handling for iqoqo's multi-faceted library navigation interface.
## Requirements
### Requirement: Intra-Facet Selection (OR)

Multiple selections within a single facet category (e.g., Category: `text` and `music`, or Format: `book` and `vinyl`) MUST behave as an `OR` operation. The system SHALL display records that match ANY of the selected values within that facet. This rule applies uniformly to ALL facet types: Media Category, Physical Kind (Format), Status, Genre, Publisher, Tag, and Collection. No facet type may use radio-button (single-select) semantics.

#### Scenario: Multi-select within Category facet returns union

- **WHEN** the user selects both "text" and "music" under Media Category
- **THEN** the result grid SHALL display records that are either text OR music
- **AND** both checkboxes SHALL appear checked simultaneously

#### Scenario: Multi-select within Physical Kind returns union

- **WHEN** the user selects "vinyl" and "cd" under Physical Kind
- **THEN** the result grid SHALL show items that are either vinyl OR cd

#### Scenario: Selecting an active facet value deselects it

- **WHEN** a facet value is already selected and the user clicks it
- **THEN** that value SHALL become deselected immediately (in-place toggle)
- **AND** this behavior SHALL work identically for Category, Physical Kind, Genre, Status, Tag, Collection, and Publisher facets

### Requirement: Inter-Facet Selection (AND)

Selections across different facet categories MUST behave as an `AND` operation. The system SHALL display only records that satisfy all active facet groups simultaneously.

#### Scenario: Cross-facet AND combination

- **WHEN** the user selects "music" under Media Category AND "vinyl" under Physical Kind AND "Jazz" under Genre
- **THEN** the result grid SHALL display only records that are music AND vinyl AND classified as Jazz

#### Scenario: OR within AND across facets

- **WHEN** the user selects "sci-fi" and "fantasy" under Genre AND "vinyl" under Physical Kind
- **THEN** the result grid SHALL show records that are (sci-fi OR fantasy) AND vinyl

### Requirement: Supported Facet Keys

The navigation panel MUST support filtering by all of the following facet types. Each facet type MUST support multi-value OR selection unless explicitly noted as single-value only in the design documentation:

- Media Category (previously named "Format" at the category level)
- Physical Kind (sub-formats within a media category)
- Language
- Genre
- Publisher
- Availability / Collection Status (Lent vs. Available vs. Wishlisted etc.) — conditionally applies based on authorization; can be used as a cross-FRBR filter in non-item views
- Progress — conditionally applies based on authorization and context
- Storage Location / User Tags
- Named Collections

#### Scenario: Genre facet filters records correctly

- **WHEN** the user selects a Genre value (e.g., "Jazz")
- **THEN** the backend SHALL return only records whose Work-level metadata contains that genre value
- **AND** the result count SHALL be non-zero when matching records exist in the library

#### Scenario: Collection Status allows cross-FRBR filtering

- **WHEN** the user is viewing a non-item view (Works, Expressions, Manifestations)
- **AND** the user selects a Collection Status filter (e.g., "wish_list")
- **THEN** the result grid SHALL show the non-item entities that contain at least one Item matching the selected collection status

#### Scenario: Tags facet cross-FRBR filtering

- **WHEN** the user selects a Tag value (e.g., "favorites") while browsing Works, Expressions, or Manifestations
- **THEN** the system SHALL return only entities that have at least one associated Item belonging to the user with that tag
- **AND** the result count SHALL reflect the number of matching entities at the current FRBR level

#### Scenario: Storage Location / Named Collections facet cross-FRBR filtering

- **WHEN** the user selects a Storage Location or Named Collection value while browsing Works, Expressions, or Manifestations
- **THEN** the system SHALL return only entities that have at least one associated Item belonging to the user with that storage location or named collection
- **AND** the result count SHALL reflect the number of matching entities at the current FRBR level

#### Scenario: Physical Kind facet cross-FRBR filtering

- **WHEN** the user selects a Physical Kind value (e.g., "Blu-ray") while browsing Works or Expressions
- **THEN** the system SHALL return only Works or Expressions that have at least one associated Manifestation with that physical kind

#### Scenario: All supported facets visible at Works/Expressions level

- **WHEN** the user is authenticated AND viewing Works or Expressions view
- **THEN** ALL supported facets SHALL be rendered (not hidden), including: Physical Kind, Collection Status, Progress, Tags, Collections, Genre, Publisher
- **AND** filtering by any of these facets SHALL reduce the displayed Works/Expressions to those associated with Items matching the filter

#### Scenario: Collection Status facet conditional rendering

- **WHEN** the user is authenticated AND viewing any FRBR level (Works, Expressions, Manifestations, Items)
- **THEN** the Collection Status facet SHALL be rendered
- **AND** it SHALL filter those views based on the collection status of their related Items belonging to the user

#### Scenario: Collection Status and Progress facets hidden when unauthenticated

- **WHEN** the user is NOT authenticated
- **THEN** the Collection Status facet SHALL NOT be rendered in any view (Global Library, Expressions, Works)
- **AND** the Progress facet SHALL NOT be rendered

### Requirement: Publisher facet filters records correctly

When a user filters by a Publisher value, the system MUST match against both the relational publisher column and any unstructured metadata fields (e.g., `meta['Publisher']`, `meta['publisher']`, and conditionally `meta['label']` for music releases). The system SHALL display records that match the publisher in any of these locations.

#### Scenario: Publisher facet matches relational column

- **WHEN** the user selects a Publisher value
- **AND** the matching publisher is stored in the `Manifestation.publisher` column
- **THEN** the backend SHALL return records associated with that publisher

#### Scenario: Publisher facet matches JSON metadata

- **WHEN** the user selects a Publisher value
- **AND** the matching publisher is stored only in the `Manifestation.meta['Publisher']` JSON field
- **THEN** the backend SHALL return records associated with that publisher

#### Scenario: Publisher faceted counts include JSON metadata

- **WHEN** the faceted sidebar generates `publisherCounts`
- **THEN** it SHALL include distinct publishers extracted and coalesced from both the relational column and the JSON `meta` fields.

### Requirement: Empty-State Requirements

When active filter combinations yield zero matching records:

- **No Crash / Blank Page:** The application MUST never render an empty page, raw JSON, or crash.
- **Empty State Component:** The UI MUST display a dedicated, styled empty-state component.
- **Reset Trigger:** A "Clear all filters" button MUST be provided.
- **Action Fallback:** A secondary button to "Add manual entry" or "Scan new barcode" MUST be offered.

#### Scenario: Zero-result state shows empty component

- **WHEN** the active filter combination returns zero records
- **THEN** the result grid SHALL be replaced by the empty-state component
- **AND** the empty-state SHALL display a "Clear all filters" button

### Requirement: Facets with no available options are hidden

If a facet group has zero selectable options AND no currently active selections from that group, the facet section MUST NOT be rendered.

#### Scenario: Empty Publishers facet is hidden

- **WHEN** no publishers exist in the current view context
- **THEN** the Publishers facet accordion section SHALL NOT be rendered

#### Scenario: Empty Physical Kind facet is hidden

- **WHEN** the active Media Category has no associated Physical Kind formats
- **THEN** the Physical Kind facet section SHALL NOT be rendered

#### Scenario: Zero-count values are not selectable

- **WHEN** cross-filtering reduces a facet value's count to zero
- **THEN** that value SHALL be hidden (not rendered or disabled) unless it is currently selected

### Requirement: Facet counts reflect the FRBR level of the current view

Facet counts shown next to facet values MUST accurately reflect the number of records at the FRBR level currently being browsed, regardless of whether the user is authenticated. Counts MUST NOT hardcode or default to Item-scoped counts when browsing higher-level entities.

#### Scenario: Global view shows Manifestation-scoped counts

- **WHEN** the user is in the global library view (manifestations scope)
- **THEN** Media Category counts SHALL reflect the total number of Manifestation records per category across the entire catalog, not just those owned by the user.

#### Scenario: Works/Expressions view shows Work/Expression-scoped counts

- **WHEN** the user is in the Works or Expressions view
- **THEN** Media Category counts SHALL reflect the number of Work or Expression records per category, not Item records

#### Scenario: Private view shows Item-scoped counts

- **WHEN** the user is in the private library view (items scope)
- **THEN** facet counts SHALL reflect the number of Item records the logged-in user owns per facet value

### Requirement: No N+1 Queries

The backend API MUST fetch facet counts using efficient SQL `GROUP BY` aggregation queries. No per-facet-value individual count queries are permitted.

#### Scenario: Facet counts returned in single aggregated response

- **WHEN** the collection page requests facet statistics
- **THEN** the backend SHALL return all facet counts (category, format, genre, publisher, status, tag) in a single API response using `GROUP BY` aggregation

### Requirement: i18n fallback guard for Progress enum values

All Progress enum values used in the `sidebar-filters.tsx` Progress facet MUST have corresponding translation keys in every supported locale file. A test MUST verify that the set of keys in the `progressLabels` map is a subset of translation keys in the default locale.

#### Scenario: Unknown Progress value falls back to English label

- **WHEN** a Progress status value exists in the database but has no matching translation key
- **THEN** the UI SHALL display the English label from the `progressLabels` map rather than the raw enum key string

#### Scenario: Progress translation coverage test catches missing keys

- **WHEN** a new Progress enum value is added to the codebase without a corresponding translation key
- **THEN** the automated translation coverage test SHALL fail and report the missing key

### Requirement: FRBR terminology is abstracted for end-users

The UI MUST NOT expose raw FRBR schema labels ("Items", "Expressions", "Manifestations", "Works") directly to end-users in the browseable collection interface.

#### Scenario: Global library uses "Releases" terminology

- **WHEN** the user is browsing the global library (manifestations scope)
- **THEN** UI labels SHALL refer to catalog entries as "Releases" or "Editions", not "Manifestations" or "Items"

#### Scenario: Private library uses "My Copies" terminology

- **WHEN** the user is browsing their private library (items scope)
- **THEN** UI labels SHALL refer to their owned records as "My Copies" or "My Items", not "Items" or "Manifestations"

### Requirement: Active filter chip row has no visible scrollbar

The horizontal scrolling container for active filter chips MUST NOT display a visible scrollbar on any platform (desktop, mobile). Scroll functionality SHALL remain available via trackpad gestures, touch swipe, or shift-scroll.

#### Scenario: Desktop browser hides scrollbar

- **WHEN** the active filter chip row contains more chips than fit the viewport width
- **THEN** the container SHALL scroll horizontally without rendering a visible scrollbar
- **AND** the user SHALL still be able to scroll using trackpad gestures or shift+scroll wheel

#### Scenario: Mobile browser hides scrollbar

- **WHEN** the active filter chip row is viewed on a mobile device
- **THEN** the container SHALL scroll horizontally via touch swipe without rendering a visible scrollbar

### Requirement: Mobile filter trigger uses secondary visual weight

The floating filter pill on mobile viewports MUST be styled as a secondary action to avoid competing with the primary Add/Scan FAB for user attention. It SHALL use a translucent, blurred background treatment (glassmorphism) rather than a solid, high-contrast fill.

#### Scenario: Filter pill uses glassmorphism styling

- **WHEN** the mobile filter pill is rendered on screens narrower than the `lg` breakpoint
- **THEN** it SHALL use a translucent dark background with backdrop blur (e.g., `bg-black/80 backdrop-blur-md`) and a subtle border (e.g., `border-white/10`)
- **AND** its visual weight SHALL be lower than any primary action button on the same screen

#### Scenario: Filter pill shows active filter count badge

- **WHEN** the user has one or more active filters
- **THEN** the filter pill SHALL display a numeric badge showing the count of active filters
- **AND** the badge SHALL use a high-contrast style to remain legible against the translucent background

### Requirement: Wishlist view action uses navigational icon

The "View Wishlist Item" dropdown action MUST use an icon that signals navigation/viewing (e.g., an eye icon) rather than reusing the same icon as the "Add to Wishlist" action. This distinction SHALL reduce cognitive friction by clearly differentiating mutation actions from navigation actions.

#### Scenario: View Wishlist uses Eye icon

- **WHEN** a manifestation already has an associated wishlist item
- **AND** the user opens the Add to Collection dropdown
- **THEN** the "View Wishlist Item" action SHALL display an `Eye` icon (not `BookmarkPlus`)

#### Scenario: Add to Wishlist retains BookmarkPlus icon

- **WHEN** a manifestation does NOT have an associated wishlist item
- **AND** the user opens the Add to Collection dropdown
- **THEN** the "Add to Wishlist" action SHALL display the `BookmarkPlus` icon
