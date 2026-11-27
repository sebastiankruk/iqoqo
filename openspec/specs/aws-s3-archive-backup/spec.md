# aws-s3-archive-backup Specification

## Purpose
Ensure cold archive backups (`make archive-run`, `archive-install`, `archive-check`, and `scripts/cloud_backup.sh --archive`) work reliably with AWS S3 / S3-compatible Glacier storage as well as `rclone` remotes.

## Requirements

### Requirement: Archive Mode Backend Selection Without Rclone Hijack

Archive scripts MUST respect `S3_BACKEND` (`auto`, `s3`, `rclone`) and MUST NOT force `rclone` when no `rclone.conf` or explicit `remote=` argument is provided.

#### Scenario: Running archive backup on an S3-only host

- **GIVEN** a host with `S3_BACKEND=auto` (or `s3`), no `~/.config/rclone/rclone.conf`, and `S3_BUCKET_ARCHIVE` (or `S3_BUCKET_BACKUP`) plus `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` set in `.env`
- **WHEN** the operator runs `make archive-run` or `./scripts/cloud_backup.sh --archive`
- **THEN** the script MUST select the `s3` backend rather than falling back to `rclone` with `iqoqo-glacier:iqoqo-archive`
- **AND** `./scripts/cloud_backup_cron.sh archive-install` MUST write a cron entry invoking `./scripts/cloud_backup.sh --archive`

### Requirement: Full S3 Environment Propagation and Archive Storage Class

S3 archive uploads MUST preserve endpoint, region, addressing style, and session token settings, and support archive bucket, prefix, and storage class overrides.

#### Scenario: Uploading cold archive to non-us-east-1 S3 bucket with Glacier storage class

- **GIVEN** `S3_REGION_NAME=eu-central-1`, `S3_BUCKET_ARCHIVE=iqoqo-cold`, `S3_ARCHIVE_PREFIX=archives/`, and `S3_ARCHIVE_STORAGE_CLASS=GLACIER`
- **WHEN** `scripts/cloud_backup.sh --archive` uploads the archive tarball via `S3Service.from_environment("backup")`
- **THEN** `S3Service` MUST initialize with `region_name="eu-central-1"`, optional `endpoint_url`, `addressing_style`, and `session_token` from environment
- **AND** `S3Service.upload_file()` MUST pass `StorageClass="GLACIER"` in `ExtraArgs` under prefix `archives/`

### Requirement: Archive-Aware Health Check Thresholds and Reachability

`scripts/cloud_backup_check.sh --archive` MUST inspect the archive destination and evaluate monthly archive freshness.

#### Scenario: Checking S3 and rclone archive health

- **GIVEN** `scripts/cloud_backup_check.sh --archive` running on a configured archive host
- **WHEN** `BACKEND=s3`
- **THEN** it MUST probe `${S3_BUCKET_ARCHIVE:-${S3_BUCKET_BACKUP}}` under `${S3_ARCHIVE_PREFIX:-archives/}` using monthly freshness thresholds (pass `<= 32` days, warn `33–45` days, fail `> 45` days)
- **AND** when `BACKEND=rclone` on remotes where `rclone about` is unsupported (such as S3/Glacier), it MUST fall back to directory listing (`rclone lsjson --max-depth 1` / `rclone lsd`) before marking the remote unreachable
