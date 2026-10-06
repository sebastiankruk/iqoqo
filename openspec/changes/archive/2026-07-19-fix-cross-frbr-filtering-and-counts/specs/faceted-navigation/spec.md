---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## MODIFIED Requirements

### Requirement: Facet counts reflect the FRBR level of the current view

Facet counts shown next to facet values MUST accurately reflect the number of records at the FRBR level currently being browsed. Counts MUST NOT hardcode or default to Item-scoped counts when browsing higher-level entities.

#### Scenario: Global view shows Manifestation-scoped counts

- **WHEN** the user is in the global library view (manifestations scope)
- **THEN** Media Category counts SHALL reflect the number of Manifestation records per category, not Item records

#### Scenario: Works/Expressions view shows Work/Expression-scoped counts

- **WHEN** the user is in the Works or Expressions view
- **THEN** Media Category counts SHALL reflect the number of Work or Expression records per category, not Item records

#### Scenario: Private view shows Item-scoped counts

- **WHEN** the user is in the private library view (items scope)
- **THEN** facet counts SHALL reflect the number of Item records the logged-in user owns per facet value

### Requirement: Supported Facet Keys

The navigation panel MUST support filtering by all of the following facet types. Each facet type MUST support multi-value OR selection unless explicitly noted as single-value only in the design documentation:

- Media Category (previously named "Format" at the category level)
- Physical Kind (sub-formats within a media category)
- Language
- Genre
- Publisher
- Availability / Collection Status (Lent vs. Available vs. Wishlisted etc.) — conditionally applies based on authorization
- Progress — conditionally applies based on authorization and context
- Storage Location / User Tags
- Named Collections

#### Scenario: Genre facet filters records correctly

- **WHEN** the user selects a Genre value (e.g., "Jazz")
- **THEN** the backend SHALL return only records whose Work-level metadata contains that genre value
- **AND** the result count SHALL be non-zero when matching records exist in the library

#### Scenario: Publisher facet filters records correctly

- **WHEN** the user selects a Publisher value
- **THEN** the backend SHALL return only records associated with that publisher

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

#### Scenario: Collection Status facet hidden when unauthenticated

- **WHEN** the user is NOT authenticated
- **THEN** the Collection Status facet SHALL NOT be rendered in any view (Global Library, Expressions, Works)
- **AND** the Progress facet SHALL NOT be rendered
