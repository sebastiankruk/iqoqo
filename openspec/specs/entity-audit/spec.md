# entity-audit Specification

## Purpose

TBD - created by archiving change architectural-hardening-phase-2. Update Purpose after archive.

## Requirements

### Requirement: Curation Audit Logging for WEM Tiers

The system SHALL maintain a dedicated audit log (`EntityAuditLog`) for tracking metadata edits, resolving duplicates, and merging records at the Work, Expression, and Manifestation tiers.

#### Scenario: Track Metadata Edit

- **WHEN** an administrator or custodian merges two Work records or modifies their metadata
- **THEN** the system logs an audit event detailing the change and the responsible user, preserving curation history independently from physical item custody.
