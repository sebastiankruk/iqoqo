# OpenSpec Specification: Cross-FRBR Entity Filtering

## Purpose

This specification defines the behavioral requirements for filtering higher-level FRBR entities (Works, Expressions, Manifestations) by attributes belonging to their associated lower-level entities (Manifestations, Items). It also defines the behavior for unauthenticated users viewing the global library.

## Requirements

### Requirement: Cross-FRBR Lower-to-Higher Entity Filtering

The system SHALL allow higher-level FRBR entities (Works, Expressions, Manifestations) to be filtered by attributes belonging to their associated lower-level entities (Manifestations, Items), provided the lower-level attributes exist within the current user's context.

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

### Requirement: Unauthenticated Context Hiding

The system SHALL hide facets and counts that depend on user-specific lower-level entities (like Items) when no user is authenticated.

#### Scenario: Unauthenticated User Views Global Library

- **WHEN** an unauthenticated user views the Global Library
- **THEN** all user-specific facets SHALL NOT be rendered: Collection Status, Progress, Tags, Storage Location, Named Collections
- **AND** the Media Category and Physical Kind counts SHALL NOT default to 0 simply because there is no user context; they MUST reflect the global counts of Manifestations/Expressions/Works.
- **AND** Expressions and Works tabs/views SHALL be visible and populated appropriately based on global data, rather than being hidden or returning 0 results due to lack of a user-specific Item context.
