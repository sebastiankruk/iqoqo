# editor/decomposition Specification

## Purpose

Provides a modular, decomposed editing architecture for FRBR entities (Work, Expression, Manifestation, Item), including visual tree navigation, dedicated contributor management, optimistic query cache synchronization, and active child creation, escalation, and deletion workflows.

## Requirements

### Requirement: Decomposed FRBR Hierarchy Editors
The system SHALL provide dedicated, decomposed editing components for each FRBR tier—`WorkEditor` (F1), `ExpressionEditor` (F2), `ManifestationEditor` (F3), and `ItemEditor` (F5)—managed within an orchestrating container rather than a monolithic editing form.

#### Scenario: Editing Work entity in dedicated editor

- **WHEN** a user selects a Work node in the FRBR hierarchy
- **THEN** the system SHALL display the `WorkEditor` exposing title, dynamic metadata fields, board game mechanics, and complex work series management without rendering input fields for other tiers

#### Scenario: Editing Expression entity in dedicated editor

- **WHEN** a user selects an Expression node in the FRBR hierarchy
- **THEN** the system SHALL display the `ExpressionEditor` exposing content type, language, expression kind, and dynamic metadata fields

#### Scenario: Editing Manifestation entity in dedicated editor

- **WHEN** a user selects a Manifestation node in the FRBR hierarchy
- **THEN** the system SHALL display the `ManifestationEditor` exposing media format selection, physical identifiers (ISBN-13, UPC, EAN), publisher, publication date, and dynamic metadata fields

#### Scenario: Editing Item entity in dedicated editor

- **WHEN** a user selects an Item node in the FRBR hierarchy
- **THEN** the system SHALL display the `ItemEditor` exposing custody status, physical condition, owner identification, and dynamic metadata fields

### Requirement: FRBR Visual Hierarchy Tree Navigator
The system SHALL render an interactive `FRBRTreeView` component displaying the complete hierarchical lineage from Work through Expressions, Manifestations, and Items with entity status indicators and node selection controls.

#### Scenario: Navigating entities via hierarchy tree

- **WHEN** a user clicks on an entity node in the `FRBRTreeView`
- **THEN** the system SHALL update the active editing view to the selected entity while highlighting the active node in the tree hierarchy

#### Scenario: Displaying entity badges and counts

- **WHEN** the `FRBRTreeView` loads the manifestation hierarchy
- **THEN** the tree SHALL display format icons, item count badges, and entity identifiers for each node in the tree

### Requirement: Contributor Attribution Editor
The system SHALL provide a `ContributorEditor` component integrated into Work, Expression, and Manifestation levels to manage person and organization attributions according to FRBR event modeling rules.

#### Scenario: Managing Work creators

- **WHEN** an authorized user accesses the `ContributorEditor` on a Work entity
- **THEN** the system SHALL allow searching and attaching contributors with creator roles (e.g., author, composer, game designer)

#### Scenario: Managing Expression realizers

- **WHEN** an authorized user accesses the `ContributorEditor` on an Expression entity
- **THEN** the system SHALL allow searching and attaching contributors with performance roles (e.g., performer, translator, narrator, illustrator)

#### Scenario: Removing contributor attribution

- **WHEN** an authorized user removes a contributor entry from an entity
- **THEN** the system SHALL delete the contribution link and immediately reflect the change in the attribution list

### Requirement: Optimistic Query Cache Synchronization
The system SHALL perform optimistic cache updates on mutations to FRBR entities in the TanStack Query cache, eliminating full-tree blocking roundtrips while rolling back changes on failure.

#### Scenario: Optimistic field update

- **WHEN** a user saves changes to an entity's fields or metadata
- **THEN** the system SHALL immediately update the TanStack Query cache with the pending values before network confirmation and render the updated values without invoking a full tree reload

#### Scenario: Mutation rollback on server failure

- **WHEN** an entity update mutation fails on the server
- **THEN** the system SHALL roll back the TanStack Query cache to its previous snapshot and display an error notification

### Requirement: Active Add Child Entity Workflow
The system SHALL provide functional "Add Child" action handlers across hierarchical levels that prompt for child details, create the entity via API, and optimistically attach it to the parent in the tree view.

#### Scenario: Adding Expression child to Work

- **WHEN** an authorized user executes "Add Child" on a Work entity
- **THEN** the system SHALL create a new Expression associated with the parent Work, insert it into the active tree state, and switch focus to the new Expression editor

#### Scenario: Adding Manifestation child to Expression

- **WHEN** an authorized user executes "Add Child" on an Expression entity
- **THEN** the system SHALL create a new Manifestation associated with the parent Expression, insert it into the active tree state, and switch focus to the new Manifestation editor

#### Scenario: Adding Item child to Manifestation

- **WHEN** an authorized user executes "Add Child" on a Manifestation entity
- **THEN** the system SHALL create a new Item associated with the parent Manifestation, append it to the items list, and open its editor

### Requirement: Active Escalate and Delete Handlers
The system SHALL provide active "Escalate" and "Delete" action handlers across all FRBR entity tiers with role-based confirmation dialogues and permission guardrails.

#### Scenario: Escalating entity change without write permission

- **WHEN** a user without write metadata permission selects "Escalate" on an entity
- **THEN** the system SHALL open the escalation request dialogue prepopulated with entity level and target identifier for custodian review

#### Scenario: Deleting an entity with confirmation

- **WHEN** an authorized user confirms deletion of an Item or leaf entity
- **THEN** the system SHALL send the deletion request, remove the entity from the query cache, and adjust the active selection to the parent entity
