## Why

We need to upgrade PostgreSQL from 16 to 18 and Redis from 7 to 8 to stay current with upstream patches and features. However, updating the PostgreSQL Docker image from 16 to 18 directly causes the database to fail to start because the existing data directory is incompatible with the new major version. This requires a safe, data-preserving migration process.

## What Changes

- Upgrade PostgreSQL image from `16-alpine` to `18-alpine` in `docker-compose.yml`.
- Upgrade Redis image from `7-alpine` to `8-alpine` in `docker-compose.yml`.
- Introduce a safe data migration script/process to dump existing data from PostgreSQL 16, upgrade the container, and restore the data into PostgreSQL 18.
- Document the upgrade path for existing users to avoid breaking their running instances.

## Capabilities

### New Capabilities

- `database-upgrade`: A safe data migration process and scripts to handle major version upgrades of stateful containers (PostgreSQL and Redis) without data loss.

### Modified Capabilities

## Impact

- `docker-compose.yml` and `docker-compose.monitoring.yml` image tags.
- The `deploy/` directory (adding migration scripts).
- End-user deployment process for existing instances.
