## Purpose

Provides typed SQL column promotion for FRBR F3 physical attributes (ISBN-13, publisher, format_type) from unstructured JSONB metadata, with validation, preflight checks, and migration safety.

## ADDED Requirements

### Requirement: F3 Attribute Validation

The system SHALL validate ISBN-13, publisher, and format_type values during manifestation creation and migration, with configurable strict/non-strict modes for format_type validation.

#### Scenario: ISBN-10 to ISBN-13 conversion with checksum validation

- **WHEN** a manifestation is created with an ISBN-10 value
- **THEN** the system SHALL convert it to ISBN-13 format with checksum validation and reject invalid ISBNs

#### Scenario: Publisher length validation

- **WHEN** a manifestation is created with a publisher value exceeding 255 characters
- **THEN** the system SHALL reject the value or truncate it according to migration policy

#### Scenario: Format type strict mode validation

- **WHEN** strict mode is enabled and a manifestation is created with an unknown format_type
- **THEN** the system SHALL reject the value with a validation error

#### Scenario: Format type non-strict mode validation

- **WHEN** non-strict mode is enabled and a manifestation is created with an unknown format_type
- **THEN** the system SHALL accept the value but log a warning about taxonomy pollution

### Requirement: F3 Migration Preflight

The system SHALL provide a preflight check that validates data quality before running the F3 column promotion migration, detecting long publishers, invalid ISBNs, ISBN conflicts, and mixed-case metadata keys.

#### Scenario: Preflight detects blocking issues

- **WHEN** the preflight check detects publisher values exceeding 255 characters or ISBN conflicts
- **THEN** the migration SHALL abort with a RuntimeError listing all blocking issues

#### Scenario: Preflight reports non-blocking issues

- **WHEN** the preflight check detects mixed-case metadata keys or other non-blocking issues
- **THEN** the migration SHALL log warnings but proceed with the migration

### Requirement: F3 Validation Documentation

The system SHALL document the strict/non-strict mode tradeoff for format_type validation, including the rationale for accepting unknown formats in non-strict mode (forward compatibility) and the risk of taxonomy pollution.

#### Scenario: Developer reads validation documentation

- **WHEN** a developer reads the f3_validation.py module docstring or format_type validation function
- **THEN** the documentation SHALL explain the strict/non-strict tradeoff and recommend strict mode for new deployments
