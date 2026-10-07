## MODIFIED Requirements

### Requirement: Idempotent Entity Reconciliation and Normalization

The system SHALL reconcile duplicate FRBR entities, merge child relationships to canonical records, and normalize ISBN values to standard 13-digit format idempotently. All dependent relationships (including ItemTag and ItemStatusLog, which follow Item reparenting transitively) SHALL be documented in the relationship inventory and either explicitly reparented or documented as implicitly handled.

#### Scenario: Merging duplicate manifestations

- **WHEN** duplicate Manifestations sharing the same normalized ISBN are processed
- **THEN** the system SHALL reassign all associated Items to the canonical Manifestation, prune redundant metadata, and remove duplicate Manifestation records

#### Scenario: Normalizing ISBN identifiers

- **WHEN** a Manifestation contains a 10-digit ISBN or hyphenated ISBN string
- **THEN** the system SHALL convert and store the canonical normalized 13-digit ISBN format

#### Scenario: Relocating misplaced ISBN identifiers

- **WHEN** an ISBN is stored on a Work entity
- **THEN** the system SHALL associate the ISBN with the corresponding child Manifestation and remove it from the Work entity

#### Scenario: Re-running ETL on clean catalog

- **WHEN** the ETL tool is executed consecutively on a catalog that has already been reconciled
- **THEN** the system SHALL make zero database modifications and report zero pending anomalies

#### Scenario: Implicit relationship handling documentation

- **WHEN** the ETL apply function processes Manifestation merges
- **THEN** inline comments SHALL document that ItemTag and ItemStatusLog are handled implicitly via Item reparenting (they reference item_id, not manifestation_id)

## ADDED Requirements

### Requirement: ETL Performance Validation at Scale

The system SHALL provide performance tests that verify the safe ETL script performs acceptably on production-scale data (10K+ rows) without excessive memory usage or timeout.

#### Scenario: ETL performance with large dataset

- **WHEN** the ETL tool processes a catalog with 10,000+ manifestations
- **THEN** the reconciliation completes within acceptable time bounds (documented in test) and memory usage remains bounded
