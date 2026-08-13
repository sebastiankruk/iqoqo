# PostgreSQL 16 → 18 and Redis 7 → 8 Upgrade Guide

> [!CAUTION]
> **This is a major database version upgrade.** PostgreSQL's data directory is
> incompatible between major versions. You **must** run the migration script
> before starting the application after pulling the updated `docker-compose.yml`.

## Overview

This release updates the database infrastructure:

- **PostgreSQL**: `16-alpine` → `18-alpine`
- **Redis**: `7-alpine` → `8-alpine`

Redis upgrades are backward-compatible (RDB files work across versions).
PostgreSQL requires a data migration because its on-disk format changed.

The migration script (`deploy/migrate-postgres-16-to-18.sh`) handles this
safely by:

1. Spinning up a temporary `postgres:16-alpine` container to dump the data
2. Backing up the old Docker volume
3. Restoring the dump into a fresh `postgres:18-alpine` container

## Supported Stacks

| Stack | `COMPOSE_PROJECT_NAME` | Volume Name |
| ----- | ---------------------- | ----------- |
| `dev` | `iqoqo-dev` | `iqoqo-dev_postgres_data` |
| `preview` | `iqoqo-preview` | `iqoqo-preview_postgres_data` |
| `prod` | `iqoqo` | `iqoqo_postgres_data` |

## Upgrade Procedure

### For Production (`prod`)

```bash
# 1. Stop the running stack
make stop prod

# 2. Pull the latest code (this updates docker-compose.yml to v18)
git pull

# 3. Run the migration script
./deploy/migrate-postgres-16-to-18.sh prod

# 4. Start with the new version
make start prod prebuilt
```

### For Preview (`preview`)

```bash
# 1. Stop the running preview stack
make stop preview

# 2. Run the migration script
./deploy/migrate-postgres-16-to-18.sh preview

# 3. Start preview
make start preview prebuilt
```

### For Development (`dev`)

```bash
# 1. Stop dev services
make stop dev

# 2. Run the migration script
./deploy/migrate-postgres-16-to-18.sh dev

# 3. Start dev
make start dev
```

## Script Options

```text
Usage: migrate-postgres-16-to-18.sh <stack> [options]

Stacks:  dev | preview | prod

Options:
  --pg-user <user>       Postgres user (default: from .env or 'iqoqo')
  --pg-password <pass>   Postgres password (default: from .env or 'changeme')
  --pg-db <db>           Postgres database (default: from .env or 'iqoqo')
  --dry-run              Show what would be done without executing
  --skip-pull            Skip pulling Docker images
  -h, --help             Show this help
```

## Dry Run

To preview what the migration will do without making changes:

```bash
./deploy/migrate-postgres-16-to-18.sh prod --dry-run
```

## Rolling Back

If the migration fails or you need to revert, the old data is preserved
in a backup volume:

```bash
# Remove the (broken) v18 volume
docker volume rm iqoqo_postgres_data

# Recreate it from the backup
docker volume create iqoqo_postgres_data
docker run --rm \
  -v iqoqo_postgres_data_v16_backup:/src:ro \
  -v iqoqo_postgres_data:/dst \
  alpine sh -c 'cp -a /src/. /dst/'
```

Then revert `docker-compose.yml` to use `postgres:16-alpine` and restart.

## After Migration

Once you've confirmed everything works, you can optionally remove the
backup volume to reclaim disk space:

```bash
docker volume rm iqoqo_postgres_data_v16_backup
```

## Troubleshooting

### "Volume is in use by running container(s)"

Stop the stack first: `make stop <stack>`

### "Volume does not exist"

The specified stack has never been started, so there's no data to migrate.
Just start it normally — it will create a fresh v18 database.

### Migration succeeded but app won't start

Check the container logs:

```bash
docker compose logs db
docker compose logs web
```

If there are schema issues, the `web` container automatically runs
`flask db upgrade` on startup to apply any pending Alembic migrations.
