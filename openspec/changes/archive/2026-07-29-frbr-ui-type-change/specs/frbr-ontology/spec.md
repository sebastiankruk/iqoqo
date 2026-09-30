## ADDED Requirements

### Requirement: Type Mutability
The system SHALL allow the core `type` attribute of an existing FRBR entity (Work, Expression, Manifestation, or Item) to be modified, provided the change maintains ontological boundaries.

#### Scenario: Backend Type Update

- **WHEN** a valid API request is made to change the `type` of a Manifestation
- **THEN** the system updates the `type` field while leaving any existing type-specific metadata (e.g., `meta` JSON) intact for potential future data migration

### Requirement: Upward Type Propagation
When a Manifestation's `type` is modified, the system SHALL adapt the parent Work and Expression upwards to ensure the new type is correctly covered without limiting to other types in the future.

#### Scenario: Upward Type Adaptation

- **WHEN** a Manifestation's `type` is changed
- **THEN** the system ensures the parent Expression and Work types are adapted upwards to remain ontologically consistent with the new Manifestation type
