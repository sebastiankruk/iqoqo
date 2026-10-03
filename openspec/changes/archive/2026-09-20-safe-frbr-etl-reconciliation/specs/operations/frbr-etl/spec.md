## ADDED Requirements

### Requirement: Relationship-Complete FRBR Merge

FRBR duplicate reconciliation MUST preserve or explicitly reparent every dependent relationship before deleting a duplicate Work or Manifestation; no related record may be lost through an implicit cascade.

#### Scenario: Duplicate Work with dependent records

- **WHEN** duplicate Works are merged and the duplicate has Expressions, WorkParts, expansion links, contributions, intents, feedback, notes, or other dependents
- **THEN** every dependent record is reparented or retained under an explicit conflict policy before the duplicate Work is deleted

#### Scenario: Duplicate Manifestation with dependent records

- **WHEN** duplicate Manifestations are merged and the duplicate has Items, ImageScans, contributions, feedback, notes, or other dependents
- **THEN** every dependent record is reparented or retained before the duplicate Manifestation is deleted

#### Scenario: Relationship conflict

- **WHEN** reparenting would violate a uniqueness or ownership constraint
- **THEN** the ETL reports the conflict and aborts the affected merge without silently deleting either relationship

### Requirement: Complete Recovery Boundary

Live reconciliation MUST require a verified recovery artifact that covers all records and relationships the operation can mutate or delete.

#### Scenario: Incomplete backup

- **WHEN** recovery data cannot represent an affected dependent table or relationship
- **THEN** live mutation is refused and the operator receives a diagnostic explaining the missing coverage

#### Scenario: Successful live reconciliation

- **WHEN** a complete recovery artifact is created and verified before mutation
- **THEN** reconciliation runs in one transactional boundary and records the artifact location and merge summary

### Requirement: Safe Dry Run

Dry-run reconciliation MUST perform no database writes and MUST report the complete proposed entity and relationship changes.

#### Scenario: Dry-run duplicate merge

- **WHEN** an operator runs dry-run mode against duplicate entities
- **THEN** the command reports proposed reparenting, conflicts, deletions, and recovery requirements without flushing or committing database changes

#### Scenario: Idempotent clean rerun

- **WHEN** reconciliation is run again after a successful merge
- **THEN** it reports no pending changes and does not mutate data
