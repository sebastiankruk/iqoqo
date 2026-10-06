## Context

As reported in our dependency update check (ses_0498), PostgreSQL 18 and Redis 8 are available and recommended for our deployment. However, simply updating the Docker image tags in `docker-compose.yml` for PostgreSQL from 16 to 18 will cause a failure because PostgreSQL's data directory is incompatible between major versions. We need a reliable migration process to avoid data loss and breaking running instances for developers and users. Redis 7 to 8 migration typically doesn't have the exact same hard failure for RDB files, but it's best to upgrade both cautiously.

This upgrade needs to support a specific deployment workflow:

- A `dev` stack is used locally on macOS.
- On the server, a database is repeatedly cloned to a `preview` stack during a release cycle.
- The `prod` stack is updated by running `git pull` *before* `make start prod prebuilt`. This means `docker-compose.yml` will already specify PostgreSQL 18 before the data volume is migrated, causing a startup failure if the migration isn't handled correctly.

## Goals / Non-Goals

**Goals:**

- Provide a safe process for dumping the existing PostgreSQL 16 database.
- Upgrade the containers to PostgreSQL 18 and Redis 8.
- Restore the data into the new PostgreSQL 18 instance.
- Provide a migration script that supports `dev`, `preview`, and `prod` environments.
- Handle the scenario where `docker-compose.yml` has already been updated to v18.

**Non-Goals:**

- Completely changing the database ORM or application schema.
- Data migrations that alter the internal application structure (only upgrading the DB engine version).

## Decisions

### 1. Data Migration Approach: pg_dump/pg_restore vs. pg_upgrade

- **Decision**: We will use `pg_dump` and `pg_restore` (or `psql` restore) orchestrated via a shell script (`deploy/migrate-postgres-16-to-18.sh`) that accepts a target stack parameter (`dev`, `preview`, or `prod`).
- **Rationale**: Since users (and the standard deployment workflow) often run `git pull` before migrating, `docker-compose.yml` might already point to v18. The script will circumvent this by spinning up a temporary standalone `postgres:16-alpine` Docker container attached directly to the stack's existing Docker volume to perform the `pg_dump`. It will then backup the old volume, provision the new one, and restore the data.
- **Alternatives**: Running a specialized `tianon/postgres-upgrade` container. A custom bash script utilizing a temporary v16 container gives us full control over volume backups and environment specificity.

### 2. Redis Upgrade

- **Decision**: Update Redis from 7 to 8 and rely on standard RDB compatibility. If RDB compatibility is an issue (often it is fine for upgrades), we can instruct users to start with a fresh cache since Redis is primarily used as a Celery broker and cache, not for persistent user data.

## Risks / Trade-offs

- [Risk] **Downtime during migration** → Mitigation: This is a self-hosted / local-first application. A few minutes of downtime for a major version upgrade is acceptable.
- [Risk] **User does `git pull` on prod before migrating** → Mitigation: The migration script is designed to handle this explicitly. It does not rely on `docker-compose.yml` being set to v16; it uses a standalone `docker run` command with the v16 image to access the old volume.
- [Risk] **Data volume naming conflicts or failed upgrades** → Mitigation: The script will explicitly rename/backup the old v16 data volume (e.g., `iqoqo_<stack>_db_data_v16_backup`) rather than deleting it, allowing for retries and safe rollbacks.
