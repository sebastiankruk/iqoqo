## 1. Migration Script

- [x] 1.1 Create `deploy/migrate-postgres-16-to-18.sh` script that accepts a stack name argument (`dev`, `preview`, `prod`).
- [x] 1.2 Add logic to the script to start a standalone `postgres:16-alpine` Docker container attached to the stack's existing data volume to dump the v16 data (accommodating for `docker-compose.yml` already being updated).
- [x] 1.3 Add logic to safely back up the old v16 Docker volume (e.g., renaming it to `_backup`) instead of deleting it.
- [x] 1.4 Add logic to create the new v18 volume and restore the SQL dump into the new container.
- [x] 1.5 Make script executable and add robust error handling.

## 2. Docker Compose Updates

- [x] 2.1 Update `docker-compose.yml` to use `postgres:18-alpine`
- [x] 2.2 Update `docker-compose.yml` to use `redis:8-alpine`
- [x] 2.3 Verify `quality.yml` or other CI workflows to ensure postgres uses `18-alpine` where applicable

## 3. Documentation

- [x] 3.1 Update `README.md` or upgrade guide to document the upgrade process for `dev`, `preview`, and `prod` stacks.
- [x] 3.2 Document the correct sequence for prod: `git pull`, then run the migration script, then `make start prod prebuilt`.
