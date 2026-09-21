## Purpose

Provides database integrity auditing, duplicate entity reconciliation, ISBN-13 normalization, and automated backup-first ETL operations for FRBR Group 1 catalog hierarchies.

## ADDED Requirements

### Requirement: FRBR Integrity Audit

The system SHALL provide an automated integrity audit tool that verifies FRBR Group 1 relationships, identifies orphaned entities, flags duplicate works or manifestations, and reports ISBN structural and placement violations.

#### Scenario: Detecting orphaned entities

- **WHEN** an Expression exists without a valid Work, a Manifestation without an Expression, or an Item without a Manifestation
- **THEN** the audit tool SHALL report the entity type, ID, and missing parent relationship

#### Scenario: Detecting duplicate entities

- **WHEN** multiple Works share matching normalized titles or multiple Manifestations share identical normalized ISBNs
- **THEN** the audit tool SHALL report candidate duplicate clusters with entity IDs

#### Scenario: Detecting ISBN placement and checksum violations

- **WHEN** an ISBN attribute is detected at the Work level, or contains invalid characters or checksum errors
- **THEN** the audit tool SHALL flag the record with the violation category and offending identifier value

### Requirement: Automated Backup Prior to Data Mutation

The system SHALL create a verified point-in-time database backup before executing any data-modifying ETL operation unless explicitly bypassed in non-mutating execution modes.

#### Scenario: Pre-execution backup creation

- **WHEN** the ETL tool is executed in write mode against the database
- **THEN** the system SHALL create a timestamped database backup archive before applying any database updates

#### Scenario: Abort mutation on backup failure

- **WHEN** the backup creation process fails or cannot write to the target backup location
- **THEN** the system SHALL terminate immediately without modifying any database records

### Requirement: Idempotent Entity Reconciliation and Normalization

The system SHALL reconcile duplicate FRBR entities, merge child relationships to canonical records, and normalize ISBN values to standard 13-digit format idempotently.

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

### Requirement: Operational Tooling Execution Interface

The system SHALL provide standardized operational commands for catalog integrity auditing, ETL reconciliation, and ontology synchronization.

#### Scenario: Running audit target

- **WHEN** an operator invokes the catalog integrity audit command
- **THEN** the system SHALL execute the audit and return an exit code indicating whether integrity violations were discovered

#### Scenario: Running dry-run ETL target

- **WHEN** an operator invokes the ETL command in dry-run mode
- **THEN** the system SHALL report all proposed reconciliation actions without applying changes or generating database writes

#### Scenario: Running ontology sync target

- **WHEN** an operator invokes the ontology synchronization command
- **THEN** the system SHALL verify semantic constraints and ontology alignment against the current catalog schema
