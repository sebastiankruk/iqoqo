# Capability: database-upgrade

## Purpose

TBD - Safe PostgreSQL and Redis upgrade process.

## Requirements

### Requirement: Safe PostgreSQL Upgrade Process

The system MUST provide a documented and automated mechanism to safely migrate data from PostgreSQL 16 to PostgreSQL 18 across multiple environments (`dev`, `preview`, `prod`).

#### Scenario: User upgrades the system across environments

- **WHEN** the user executes the database upgrade script and provides an environment stack name
- **THEN** the system uses a standalone PostgreSQL 16 container to create a logical dump of the specified stack's database volume
- **THEN** the system backs up the old volume and provisions a new PostgreSQL 18 volume
- **THEN** the system restores the logical dump into the new volume

#### Scenario: Upgrading the prod environment after git pull

- **GIVEN** the `docker-compose.yml` has already been updated to specify PostgreSQL 18
- **WHEN** the user executes the database upgrade script for `prod`
- **THEN** the script successfully dumps the v16 data by ignoring the `docker-compose.yml` and mounting the data directly to a standalone v16 container
- **THEN** the normal startup process (`make start prod prebuilt`) correctly uses the newly migrated v18 data

### Requirement: Redis Upgrade

The system MUST upgrade the Redis container to version 8.

#### Scenario: Upgrading Redis cache

- **WHEN** the system is started with the new configuration
- **THEN** Redis 8 is initialized and available for Celery and caching

### Requirement: Two-Stage Linear Alembic Migration Pipeline
The database migration pipeline MUST consist of a historical baseline migration representing the exact canonical state of release v0.7.17 (`v0_7_17_baseline`) and a linear incremental migration (`v0_7_18_fixes`) containing all schema modifications introduced in v0.7.18.

#### Scenario: Running migrations on a fresh empty database
- **WHEN** `flask db upgrade` executes on an empty database
- **THEN** Alembic executes `v0_7_17_baseline` to create the 0.7.17 schema
- **THEN** Alembic executes `v0_7_18_fixes` to apply 0.7.18 updates (`auth.token_blocklist.expires_at`, `config.instance_settings`, CheckConstraints)
- **THEN** the final database schema matches current application models with head `v0_7_18_fixes`

### Requirement: Automated Backward-Compatible Migration Bridge
The system MUST provide an automated migration bridge that detects legacy 0.7.17 production revisions (including `f65648a6aaf4`), stamps the database with `v0_7_17_baseline` without re-creating historical tables, and allows standard `flask db upgrade` to execute subsequent migration scripts.

#### Scenario: Upgrading an existing 0.7.17 production database
- **GIVEN** a database at revision `f65648a6aaf4`
- **WHEN** the container boots or `flask db upgrade` executes
- **THEN** the bridge detects `f65648a6aaf4` and stamps `v0_7_17_baseline`
- **THEN** Alembic executes `v0_7_18_fixes` to alter `auth.token_blocklist`, move `instance_settings` to `config`, and add check constraints
- **THEN** the database version advances to `v0_7_18_fixes` without requiring manual SQL fixes in cloning scripts

