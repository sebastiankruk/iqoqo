# frontend-architecture Specification

## Purpose

Defines requirements for synchronized query cache invalidation, dead code elimination, interim stabilization of FRBR Editor controls pending the v0.8.0 milestone, and declarative polling.

## Requirements

### Requirement: Synchronized Query Cache Keys
The system SHALL standardize TanStack React Query cache key arrays across all mutation triggers and query hooks, ensuring instant UI synchronization across views.

#### Scenario: Mutating collection membership

- **WHEN** a user adds or removes an item from a collection
- **THEN** corresponding collection, shelf, and item queries are invalidated with matching key tuples, refreshing affected UI components immediately

### Requirement: FRBR Editor Interim UI Stabilization
The system SHALL disable or conditionally suppress unwired buttons and menu actions in the FRBR Editor, presenting clear feedback regarding features slated for v0.8.0.

#### Scenario: Interacting with child creation controls in FRBR Editor

- **WHEN** a user interacts with "Add Child" or unlinked contextual dropdown actions
- **THEN** controls are visibly disabled and provide tooltip context ("Coming in v0.8.0") to prevent confusion

### Requirement: Declarative Query Polling
The system SHALL manage recurring background queries using TanStack Query's declarative `refetchInterval` rather than manual `setInterval` handles.

#### Scenario: Waiting for background image processing

- **WHEN** a manifestation displays pending cover art processing
- **THEN** the status query polls on a declarative interval and stops automatically once processing completes or the view changes

### Requirement: Dead Frontend Code Pruning
The system SHALL prune unused exported API client methods and duplicate select options from UI components.

#### Scenario: Building frontend client bundle

- **WHEN** the frontend application compiles
- **THEN** unused helper functions such as uncalled manifestation lookups are pruned from the bundle
