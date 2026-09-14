# database-schema-migrations Specification

## Purpose

Defines requirements for consolidating database migration history into a single baseline, providing an automated upgrade bridge for clean 0.7.17 production databases, isolating configuration settings, and extracting data backfills.

## Requirements

### Requirement: Consolidated Baseline Migration
The system SHALL consolidate all historical database migrations into a single linear baseline migration `v0_7_18_baseline` that represents the canonical v0.7.18 schema.

#### Scenario: Initializing fresh database

- **WHEN** `flask db upgrade` is executed on an empty database
- **THEN** all schemas, tables, indexes, and constraints are created directly from `v0_7_18_baseline` in a single pass

### Requirement: Automated Production Upgrade Bridge for Head f65648a6aaf4
The system SHALL detect existing production databases at revision `f65648a6aaf4` (clean v0.7.17 head) and stamp them to `v0_7_18_baseline` without executing duplicate DDL or raising missing-revision errors.

#### Scenario: Upgrading clean v0.7.17 production database

- **WHEN** a production instance at revision `f65648a6aaf4` executes the upgrade process
- **THEN** the upgrade bridge stamps the database to `v0_7_18_baseline` without error, preserving all data and preparing for subsequent migrations

### Requirement: Decoupling Data Migrations from Schema DDL
The system SHALL execute heavy data repairs and backfills through standalone operational scripts rather than within Alembic migration transactions.

#### Scenario: Running schema migrations during container deployment

- **WHEN** database migration commands run during deployment
- **THEN** only structural schema DDL is executed and no unbounded table scans or mass row updates occur inside migration transactions

### Requirement: Configuration Schema Isolation and Foreign Key Integrity
The system SHALL place instance settings in a dedicated `config` schema and declare explicit cascading or nullifying behaviors on foreign keys.

#### Scenario: Deleting referenced user or entity

- **WHEN** an entity referenced by optional relationships is deleted
- **THEN** referencing foreign keys are safely set to NULL rather than causing integrity constraint violations
