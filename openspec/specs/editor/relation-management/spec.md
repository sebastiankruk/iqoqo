# editor/relation-management Specification

## Purpose

Provides administrative capabilities and backend services to restructure, reassign, merge, and split FRBR hierarchy entities while enforcing strict ontological boundaries and single-level roadmap item normalization.

## Requirements

### Requirement: FRBR Entity Reassignment

The system SHALL allow authorized administrators to reassign parent-child relationships between adjacent FRBR levels (moving an Expression to a new parent Work, moving a Manifestation to a new parent Expression, or moving an Item to a new parent Manifestation). The system SHALL reject any reassignment that shortcuts or violates the four-tier FRBR hierarchy (Work -> Expression -> Manifestation -> Item).

#### Scenario: Reassigning Manifestation to another Expression

- **WHEN** an administrator submits a request to reassign Manifestation `M1` from Expression `E1` to Expression `E2`
- **THEN** the parent relationship of `M1` is updated to `E2`, all child Items of `M1` remain attached to `M1`, and an audit record is logged

#### Scenario: Reassigning Expression to another Work

- **WHEN** an administrator submits a request to reassign Expression `E1` from Work `W1` to Work `W2`
- **THEN** the parent relationship of `E1` is updated to `W2`, all child Manifestations and Items of `E1` remain attached under `E1`, and an audit record is logged

#### Scenario: Rejection of invalid cross-level assignment

- **WHEN** an administrator attempts to assign a Manifestation directly to a Work or an Item directly to an Expression
- **THEN** the system rejects the request with a validation error indicating that hierarchy levels cannot be bypassed

### Requirement: FRBR Entity Merge

The system SHALL allow authorized administrators to merge two entities of the same FRBR level (Work into Work, Expression into Expression, or Manifestation into Manifestation). During a merge, all child entities of the source entity SHALL be reparented to the target entity, non-conflicting metadata SHALL be merged, and the source entity SHALL be removed. Merging entities across differing FRBR levels SHALL be strictly prohibited.

#### Scenario: Merging duplicate Works

- **WHEN** an administrator merges source Work `W_source` into target Work `W_target`
- **THEN** all Expressions attached to `W_source` are reparented to `W_target`, non-conflicting metadata from `W_source` is merged into `W_target`, and `W_source` is removed

#### Scenario: Merging duplicate Manifestations

- **WHEN** an administrator merges source Manifestation `M_source` into target Manifestation `M_target`
- **THEN** all Items attached to `M_source` are reparented to `M_target`, identifiers (ISBN-13, UPC, EAN) are reconciled, and `M_source` is removed

#### Scenario: Rejection of cross-level entity merge

- **WHEN** an administrator attempts to merge a Work with an Expression or an Expression with a Manifestation
- **THEN** the system rejects the request with a 400 Bad Request error indicating that merge operations are only valid between entities of the same FRBR level

### Requirement: FRBR Entity Split

The system SHALL allow authorized administrators to split an entity by extracting a selected subset of its child nodes into a newly created sibling entity at the same FRBR level.

#### Scenario: Splitting Expressions into a new Work

- **WHEN** an administrator selects one or more Expressions under Work `W1` and executes a split with title `W2_title`
- **THEN** a new Work `W2` is created with `W2_title`, the selected Expressions are reparented to `W2`, and unselected Expressions remain under `W1`

#### Scenario: Splitting Manifestations into a new Expression

- **WHEN** an administrator selects one or more Manifestations under Expression `E1` and executes a split with specified language and content type
- **THEN** a new Expression `E2` is created under the same parent Work, the selected Manifestations are reparented to `E2`, and unselected Manifestations remain under `E1`

#### Scenario: Splitting Items into a new Manifestation

- **WHEN** an administrator selects one or more Items under Manifestation `M1` and executes a split with new edition details
- **THEN** a new Manifestation `M2` is created under the same parent Expression, the selected Items are reparented to `M2`, and unselected Items remain under `M1`

### Requirement: Roadmaps Single-FRBR-Level Normalization

Each reading roadmap item SHALL reference strictly a single FRBR entity level: either a Work, an Expression, or a Manifestation. The system SHALL enforce this mutual exclusivity constraint at both the database schema layer and API validation layer.

#### Scenario: Creating a roadmap item linked strictly to a Work

- **WHEN** a user adds an item to a roadmap specifying only `work_id`
- **THEN** the roadmap item is persisted with `work_id` populated and `expression_id` and `manifestation_id` set to null

#### Scenario: Creating a roadmap item linked strictly to an Expression

- **WHEN** a user adds an item to a roadmap specifying only `expression_id`
- **THEN** the roadmap item is persisted with `expression_id` populated and `work_id` and `manifestation_id` set to null

#### Scenario: Creating a roadmap item linked strictly to a Manifestation

- **WHEN** a user adds an item to a roadmap specifying only `manifestation_id`
- **THEN** the roadmap item is persisted with `manifestation_id` populated and `work_id` and `expression_id` set to null

#### Scenario: Rejection of ambiguous multi-level or zero-level roadmap item

- **WHEN** an API request attempts to create or update a roadmap item with multiple entity references (e.g. both `work_id` and `manifestation_id`) or no entity references
- **THEN** the request is rejected with a 400 Bad Request error indicating that exactly one FRBR level must be referenced

### Requirement: Relation Management Authorization and Audit Logging

All relation reassign, merge, and split actions SHALL require authenticated administrator access with write metadata permissions. Every structural relation modification SHALL generate an immutable audit log entry capturing the mutation type, source entity, target entity, and user identity.

#### Scenario: Unauthorized relation modification attempt

- **WHEN** an unauthenticated client or a user lacking write metadata permissions attempts a relation reassign, merge, or split
- **THEN** the request is denied with a 401 Unauthorized or 403 Forbidden status code

#### Scenario: Successful relation modification audit trail

- **WHEN** an authorized administrator performs any reassignment, merge, or split operation
- **THEN** an audit log entry is saved recording the entity type, entity ID, previous parent ID, new parent ID, and acting user ID

### Requirement: Relation Management UI Impact Preview and Confirmation

The administrative FRBR editor UI SHALL provide interactive workflows to trigger reassign, merge, and split operations, displaying an impact preview of affected downstream child entities and requiring explicit confirmation before changes are executed.

#### Scenario: Impact preview displayed prior to merge confirmation

- **WHEN** an administrator selects a target entity for a merge operation in the UI
- **THEN** the UI displays an impact summary showing the number of child Expressions, Manifestations, and Items that will be transferred

#### Scenario: Confirmation commits relation changes and refreshes editor tree

- **WHEN** the administrator confirms the relation modification dialog
- **THEN** the API mutation executes, a success notification is shown, and the visual FRBR tree is re-fetched and updated
