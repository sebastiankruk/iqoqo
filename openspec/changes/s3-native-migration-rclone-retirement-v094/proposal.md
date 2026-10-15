## Why
Simplifies deployment, eliminates host binary dependencies, and guarantees that the `federation` database schema and encrypted keys are fully verified during cloud backups.
## What Changes

- Retire residual `rclone` container mounts and host dependencies.
- Route cloud backup uploads directly through `app/core/s3_service.py` (`boto3`) and `S3_BACKEND` in `scripts/cloud_backup.sh`.
- Include `federation` PostgreSQL schema in database dumps, restore verification, and preflight checks.
- Update `tests/bash/cloud_backup.bats` and `docs/BACKUPS.md`.

## Capabilities

### New Capabilities
- `s3-native-backup-migration`: Retire residual rclone dependencies in favor of native S3 service and include federation schema in backups

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Simplifies `docker-compose.yml`, modifies backup shell scripts and BATS test suites.
