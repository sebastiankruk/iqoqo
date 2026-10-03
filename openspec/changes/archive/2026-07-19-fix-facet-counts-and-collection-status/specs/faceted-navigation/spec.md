---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## MODIFIED Requirements

### Requirement: Facet counts reflect the FRBR level of the current view

Facet counts shown next to facet values MUST accurately reflect the number of records at the FRBR level currently being browsed, regardless of whether the user is authenticated.

#### Scenario: Global view shows Manifestation-scoped counts

- **WHEN** the user is in the global library view (manifestations scope)
- **THEN** Media Category counts SHALL reflect the total number of Manifestation records per category across the entire catalog, not just those owned by the user.

#### Scenario: Private view shows Item-scoped counts

- **WHEN** the user is in the private library view (items scope)
- **THEN** facet counts SHALL reflect the number of Item records the logged-in user owns per facet value.

### Requirement: Supported Facet Keys

The navigation panel MUST support filtering by all of the following facet types. Each facet type MUST support multi-value OR selection unless explicitly noted as single-value only in the design documentation:

- Media Category (previously named "Format" at the category level)
- Physical Kind (sub-formats within a media category)
- Language
- Genre
- Publisher
- Availability / Collection Status (Lent vs. Available vs. Wishlisted etc.) — applies to Items, but can be used as a cross-FRBR filter in non-item views.
- Progress — applies to Items (private library) only, contextual to active Media Category
- Storage Location / User Tags
- Named Collections

#### Scenario: Genre facet filters records correctly

- **WHEN** the user selects a Genre value (e.g., "Jazz")
- **THEN** the backend SHALL return only records whose Work-level metadata contains that genre value
- **AND** the result count SHALL be non-zero when matching records exist in the library

#### Scenario: Publisher facet filters records correctly

- **WHEN** the user selects a Publisher value
- **THEN** the backend SHALL return only records associated with that publisher

#### Scenario: Collection Status allows cross-FRBR filtering

- **WHEN** the user is viewing a non-item view (Works, Expressions, Manifestations)
- **AND** the user selects a Collection Status filter (e.g., "wish_list")
- **THEN** the result grid SHALL show the non-item entities that contain at least one Item matching the selected collection status.
