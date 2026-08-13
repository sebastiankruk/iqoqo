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
