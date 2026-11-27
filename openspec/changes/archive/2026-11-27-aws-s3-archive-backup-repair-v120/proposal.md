## Why

AWS S3 & Glacier cold archive backups (`make archive-run`, `make archive-install`, `make archive-check`) currently fail on S3-configured hosts and non-default S3 environments due to several integration defects:

1. `Makefile` `archive-run` unconditionally passes `iqoqo-glacier:iqoqo-archive` as `$1` to `scripts/cloud_backup.sh`, triggering `BACKEND="rclone"` even when `S3_BACKEND=auto` and no rclone config exists.
2. `scripts/cloud_backup.sh` lacks an `--archive` mode (`S3_BUCKET_ARCHIVE`, `S3_ARCHIVE_PREFIX` defaulting to `archives/`, and optional `S3_ARCHIVE_STORAGE_CLASS` such as `GLACIER` / `DEEP_ARCHIVE` / `GLACIER_IR`), and `scripts/cloud_backup_cron.sh archive-install` omits `--archive` from the generated cron command.
3. `scripts/cloud_backup.sh` constructs `S3Service("backup", access_key=..., secret_key=...)` directly instead of `S3Service.from_environment("backup")`, dropping `S3_ENDPOINT_URL`, `S3_REGION_NAME`, `S3_ADDRESSING_STYLE`, and `AWS_SESSION_TOKEN`.
4. `scripts/cloud_backup_check.sh --archive` still probes `S3_BUCKET_BACKUP` and `backups/` with daily 24h/48h freshness thresholds instead of `S3_BUCKET_ARCHIVE` / `archives/` with monthly archive thresholds, and fails on S3/Glacier rclone remotes because `rclone about` is unsupported there.

## What Changes

- **Makefile (`archive-run`, `archive-install`, `archive-check`):** Stop injecting `iqoqo-glacier:iqoqo-archive` when `remote` is unset; pass `--archive` (and optional `remote` only when explicitly provided) to `scripts/cloud_backup.sh` and `scripts/cloud_backup_check.sh`.
- **Backup & Cron Scripts (`scripts/cloud_backup.sh`, `scripts/cloud_backup_cron.sh`, `scripts/cloud_backup_check.sh`):**
  - Add `--archive` flag support in `cloud_backup.sh` and wire `cloud_backup_cron.sh archive-install` to invoke `./scripts/cloud_backup.sh --archive`.
  - Resolve `S3_BUCKET_ARCHIVE:-S3_BUCKET_BACKUP`, `S3_ARCHIVE_PREFIX` (default `archives/`), and `S3_ARCHIVE_STORAGE_CLASS` when `--archive` is active.
  - Use `S3Service.from_environment("backup")` so `S3_REGION_NAME`, `S3_ENDPOINT_URL`, `S3_ADDRESSING_STYLE`, and `AWS_SESSION_TOKEN` are preserved.
  - Update `cloud_backup_check.sh --archive` to inspect `S3_BUCKET_ARCHIVE` + `archives/` with monthly freshness thresholds (~32d warn / ~45d fail) and fall back from `rclone about` to `rclone lsd` / `rclone lsjson --max-depth 1` for S3/Glacier remotes.
- **S3 Service & Env Template (`app/core/s3_service.py`, `.env.example`):** Add optional `storage_class: str | None = None` support to `S3Service.upload_file()` (`ExtraArgs["StorageClass"]`), and document `S3_BUCKET_ARCHIVE`, `S3_ARCHIVE_PREFIX`, and `S3_ARCHIVE_STORAGE_CLASS` in `.env.example`.

## Impact

- Affected files: `Makefile`, `scripts/cloud_backup.sh`, `scripts/cloud_backup_cron.sh`, `scripts/cloud_backup_check.sh`, `app/core/s3_service.py`, `.env.example`, `tests/test_s3_service.py`, `tests/bash/`.
- No database migrations, no FRBR schema changes, backward-compatible with existing daily backup configurations (`rclone` and `s3`).
