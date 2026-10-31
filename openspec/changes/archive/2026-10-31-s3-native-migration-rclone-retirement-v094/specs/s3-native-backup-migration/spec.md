## Purpose
Preserve dual-mode (`rclone` + native S3) host backups while guaranteeing that the `federation` PostgreSQL schema and instance actor keys (`data/federation_keys`) are archived and restored intact.

## ADDED Requirements

### Requirement: Dual-Backend Cloud Backup and Federation Key Preservation

The backup system SHALL preserve dual-backend upload support (`S3_BACKEND=auto|rclone|s3`) on the host so operators can sync archives via either `rclone` (Dropbox, Google Drive, OneDrive, WebDAV, SFTP) or native S3 (`app/core/s3_service.py` / `boto3`), and SHALL archive both the full PostgreSQL dump (including the `federation` schema and encrypted actor keys) and `data/federation_keys` (`server.pem`).

#### Scenario: Dual-mode backup supports both rclone and native S3 backends
- **WHEN** `scripts/cloud_backup.sh` executes with `S3_BACKEND=rclone` (or `auto` with `rclone.conf` present) or `S3_BACKEND=s3`
- **THEN** the script SHALL upload the compressed backup archive using the selected backend without removing `rclone` support for non-S3 storage providers.

#### Scenario: Backup and restore include federation schema and instance RSA key
- **WHEN** `scripts/cloud_backup.sh` and `scripts/restore.sh` execute when `data/federation_keys` exists
- **THEN** `scripts/cloud_backup.sh` SHALL include `data/federation_keys` in `ASSET_PATHS` alongside the `pg_dumpall` database dump (`federation` schema), and `scripts/restore.sh` SHALL restore `data/federation_keys` with owner-only permissions (`0700` directory / `0600` key files).

