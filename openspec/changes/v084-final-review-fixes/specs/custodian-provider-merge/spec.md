## MODIFIED Requirements

### Requirement: Interactive Multi-Provider Fragment Comparison

The system SHALL provide an interface for authorized custodians displaying genuine metadata fragments retrieved from external providers side-by-side grouped by FRBR tier. Candidate values SHALL be extracted from authentic provider payloads or recorded entity provenance without hardcoding synthetic test values. The interface SHALL dynamically synchronize candidate options and selected provider states whenever entity hierarchy data updates.

#### Scenario: Comparing metadata fragments across providers

- **WHEN** a custodian opens the Provider Merge Disambiguation view for a manifestation
- **THEN** the interface displays candidate attributes extracted from genuine provider responses and recorded provenance side-by-side
- **AND** groups fields under Work (F1), Expression (F2), and Manifestation (F3) tiers
- **AND** synchronizes selection states whenever the underlying entity tree updates.

### Requirement: Per-Field Attribute Selection and Atomic Application

The system SHALL permit custodians to choose individual winning attributes per field and apply the reconciled entity state atomically. When reconciling manifestation cover art, the system SHALL update both the top-level `manifestation.cover_url` database column and `manifestation.meta["cover_url"]` to prevent attribute shadowing. Transactions modifying multiple FRBR entities during merge SHALL acquire row-level locks strictly in canonical hierarchy order (Work -> Expression -> Manifestation) to prevent transaction deadlocks.

#### Scenario: Custodian selects attributes and confirms merge

- **WHEN** a custodian selects Title and Authors from Provider A and Cover Image from Provider B
- **AND** submits the reconciled metadata
- **THEN** the backend updates the Work and Manifestation entities in a single database transaction
- **AND** updates both the `manifestation.cover_url` column and `manifestation.meta["cover_url"]` attribute
- **AND** locks affected entities in canonical FRBR hierarchy order (Work -> Expression -> Manifestation)
- **AND** updates the entity field-level provenance to record the custodian's explicit selections
- **AND** records an entry in the EntityAuditLog with the before-and-after attribute diff.

#### Scenario: Unauthorized user denied merge action

- **WHEN** a user without `WRITE_METADATA` permission attempts to submit a provider merge
- **THEN** the system denies the request with HTTP 403 Forbidden.
