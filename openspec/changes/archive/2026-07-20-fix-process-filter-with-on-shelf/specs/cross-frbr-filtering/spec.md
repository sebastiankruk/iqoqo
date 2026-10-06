---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## MODIFIED Requirements

### Requirement: Cross-FRBR Lower-to-Higher Entity Filtering

The system SHALL allow higher-level FRBR entities (Works, Expressions, Manifestations) to be filtered by attributes belonging to their associated lower-level entities (Manifestations, Items), provided the lower-level attributes exist within the current user's context. When multiple lower-level filters are selected simultaneously (e.g., Status and Process), they MUST be combined using a logical AND condition within the same lower-level entity context.

#### Scenario: Filtering Works/Expressions by Item Status

- **WHEN** the user is viewing Works or Expressions AND selects a Collection Status facet (e.g., "wishlist")
- **THEN** the system SHALL return only Works or Expressions that have at least one associated Item belonging to the user with that specific status

#### Scenario: Filtering Works/Expressions by Manifestation-Level Attributes

- **WHEN** the user is viewing Works or Expressions AND selects a Manifestation-level facet filter (e.g., Media Category "Want to Play", Physical Kind "Blu-ray")
- **THEN** the system SHALL return only Works or Expressions that have at least one associated Manifestation matching the selected attribute(s)

#### Scenario: Filtering Works/Expressions by Tags

- **WHEN** the user is viewing Works or Expressions AND selects a Tag facet (e.g., "favorites")
- **THEN** the system SHALL return only Works or Expressions that have at least one associated Item belonging to the user with that tag

#### Scenario: Filtering Works/Expressions by Storage Location or Named Collections

- **WHEN** the user is viewing Works or Expressions AND selects a Storage Location or Named Collection facet
- **THEN** the system SHALL return only Works or Expressions that have at least one associated Item belonging to the user with that storage location or named collection

#### Scenario: Combining Item Status and Item Process Filters

- **WHEN** the user is viewing Works or Expressions AND selects both an Item Status/Location filter (e.g., "On Shelf") AND an Item Process filter (e.g., "Unread")
- **THEN** the system SHALL return only Works or Expressions that have at least one associated Item belonging to the user that is BOTH "On Shelf" AND "Unread"
- **AND** the system SHALL NOT ignore the Process filter and return all "On Shelf" items.
