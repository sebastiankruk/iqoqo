## Why
Preserves dual-backend cloud backup flexibility (`rclone` for consumer clouds like Dropbox/Google Drive/WebDAV + native `boto3` S3 for object storage) while closing the federation disaster-recovery gap by archiving `data/federation_keys` (`server.pem`) and verifying the `federation` PostgreSQL schema during backups and restores.

## What Changes

- Preserve host-side `S3_BACKEND=auto|rclone|s3` dual-backend support in `scripts/cloud_backup.sh` (in-container `rclone` was already retired in v0.8.4 in favor of `app/core/s3_service.py`).
- Add `data/federation_keys` (`server.pem` instance actor RSA key) to `ASSET_PATHS` in `scripts/cloud_backup.sh` and restore extraction in `scripts/restore.sh` with strict file permissions.
- Verify `federation` PostgreSQL schema (`pg_dumpall`) and `data/federation_keys` archive inclusion in `tests/bash/cloud_backup.bats` and `docs/BACKUPS.md`.

## Capabilities

### New Capabilities
- `s3-native-backup-migration`: Preserve dual-mode (`rclone` + native S3) host backups and include `federation` schema and `data/federation_keys` (`server.pem`) in backup and restore workflows

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Updates `scripts/cloud_backup.sh`, `scripts/restore.sh`, `tests/bash/cloud_backup.bats`, and `docs/BACKUPS.md` without removing host `rclone` support.
