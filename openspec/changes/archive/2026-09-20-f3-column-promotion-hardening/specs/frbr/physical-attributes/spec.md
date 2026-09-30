## ADDED Requirements

### Requirement: Safe F3 Column Promotion

Promoting physical Manifestation attributes from metadata MUST be safe for existing deployments, preserve data according to an explicit policy, and fail before schema mutation when preconditions are not met.

#### Scenario: Existing publisher exceeds target length

- **WHEN** migration preflight finds a publisher longer than the target column limit
- **THEN** migration follows the documented truncate/reject/expand policy before changing the column and reports affected records

#### Scenario: Mixed-case legacy metadata

- **WHEN** legacy metadata contains promoted keys with casing variants
- **THEN** the migration/service boundary applies the documented case-insensitive extraction policy without silently losing the value

#### Scenario: Reversible downgrade or explicit backup contract

- **WHEN** an operator downgrades or rolls back the promotion
- **THEN** promoted values are restored according to the documented reversibility contract, or the operation is blocked unless the required backup exists

### Requirement: Canonical Runtime Physical Attributes

Runtime F3 writes MUST normalize and validate ISBN, publisher, and format values before persistence.

#### Scenario: Valid ISBN-10 or hyphenated ISBN

- **WHEN** a valid ISBN-10 or hyphenated ISBN is supplied
- **THEN** the stored ISBN-13 column contains the canonical ISBN-13 value

#### Scenario: Invalid ISBN-13

- **WHEN** an ISBN-13 value has invalid length or checksum
- **THEN** the write is rejected with a structured validation error and no malformed ISBN-13 value is persisted

#### Scenario: Format type validation

- **WHEN** a format type is supplied
- **THEN** it is normalized and validated against the shared taxonomy or documented forward-compatible vocabulary rules before persistence
