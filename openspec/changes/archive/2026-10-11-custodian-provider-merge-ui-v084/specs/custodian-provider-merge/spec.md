## Purpose

Enables custodians to inspect metadata fragments from multiple external data providers side-by-side and choose preferred attributes per FRBR tier to synthesize a canonical description.

## ADDED Requirements

### Requirement: Interactive Multi-Provider Fragment Comparison
The system SHALL provide an interface for authorized custodians displaying metadata fragments retrieved from external providers side-by-side grouped by FRBR tier.

#### Scenario: Comparing metadata fragments across providers

- **WHEN** a custodian opens the Provider Merge Disambiguation view for a manifestation
- **THEN** the interface displays candidate attributes from all available provider responses side-by-side
- **AND** groups fields under Work (F1), Expression (F2), and Manifestation (F3) tiers.

### Requirement: Per-Field Attribute Selection and Atomic Application
The system SHALL permit custodians to choose individual winning attributes per field and apply the reconciled entity state atomically.

#### Scenario: Custodian selects attributes and confirms merge

- **WHEN** a custodian selects Title and Authors from Provider A and Cover Image from Provider B
- **AND** submits the reconciled metadata
- **THEN** the backend updates the Work and Manifestation entities in a single database transaction
- **AND** updates the entity field-level provenance to record the custodian's explicit selections
- **AND** records an entry in the EntityAuditLog with the before-and-after attribute diff.

#### Scenario: Unauthorized user denied merge action

- **WHEN** a user without `WRITE_METADATA` permission attempts to submit a provider merge
- **THEN** the system denies the request with HTTP 403 Forbidden.
