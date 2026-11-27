## Context

`scripts/cloud_backup.sh`, `scripts/cloud_backup_cron.sh`, and `scripts/cloud_backup_check.sh` already support both `rclone` and `boto3`/`S3Service` for daily backups (`make backup-run`). Cold archives (`make archive-run`, `make archive-install`, `make archive-check`) share those scripts, but several archive-specific seams were left wired for rclone-only defaults or daily backup paths.

## Goals / Non-Goals

- **Goals:**
  - Make `make archive-run`, `make archive-install`, and `make archive-check` work seamlessly with both AWS S3 / S3-compatible Glacier buckets (`S3_BACKEND=s3` or `auto`) and explicit `rclone` archive remotes.
  - Preserve full S3 environment settings (`S3_REGION_NAME`, `S3_ENDPOINT_URL`, `S3_ADDRESSING_STYLE`, `AWS_SESSION_TOKEN`) via `S3Service.from_environment`.
  - Support optional S3 storage class selection (`S3_ARCHIVE_STORAGE_CLASS`, e.g., `GLACIER`, `DEEP_ARCHIVE`, `GLACIER_IR`) during archive uploads.
  - Ensure `cloud_backup_check.sh --archive` evaluates archive buckets, archive prefixes, monthly freshness windows, and rclone remotes that reject `rclone about`.
- **Non-Goals:**
  - Implementing automated S3 lifecycle policy creation via boto3/IAM (buckets manage retention via AWS/S3 lifecycle rules as documented).
  - Adding an in-container backup daemon or modifying FRBR/API routes.

## Decisions

1. **Explicit `--archive` flag in `cloud_backup.sh`:**
   - Parse optional leading `--archive` before optional `[rclone_remote]`.
   - Under `--archive`:
     - S3 target bucket resolves `${S3_BUCKET_ARCHIVE:-${S3_BUCKET_BACKUP:-}}` (matching `cloud_backup_cron.sh`).
     - S3 prefix resolves `${S3_ARCHIVE_PREFIX:-archives/}` (normalized with trailing `/`).
     - Storage class resolves `${S3_ARCHIVE_STORAGE_CLASS:-}` and is passed to `service.upload_file(..., storage_class=...)`.
     - rclone default remote (only when `BACKEND="rclone"` and no explicit remote argument or `RCLONE_REMOTE_ARCHIVE` is set) falls back to `iqoqo-glacier:iqoqo-archive`.
2. **Stop `Makefile` from hijacking `S3_BACKEND=auto`:**
   - `archive-run` passes `--archive $(if $(remote),$(remote),)` so `$1` is never populated with `iqoqo-glacier:iqoqo-archive` unless the operator explicitly passes `remote=...` or configures `RCLONE_REMOTE_ARCHIVE` with `rclone`.
3. **Use `S3Service.from_environment("backup")` in `cloud_backup.sh`:**
   - Replaces manual `S3Service("backup", access_key=..., secret_key=...)` instantiation so `S3_REGION_NAME`, `S3_ENDPOINT_URL`, `S3_ADDRESSING_STYLE`, and `AWS_SESSION_TOKEN` are always honored.
   - `S3Service.upload_file(..., storage_class: str | None = None)` merges `StorageClass` into `ExtraArgs` only when non-empty.
4. **Archive-aware health checks in `cloud_backup_check.sh --archive`:**
   - Check `S3_BUCKET_ARCHIVE:-S3_BUCKET_BACKUP` and `${S3_ARCHIVE_PREFIX:-archives/}` instead of `S3_BUCKET_BACKUP` / `backups/`.
   - Use monthly freshness thresholds when `IS_ARCHIVE=true` (pass `<= 32` days, warn `33–45` days, fail `> 45` days) vs daily thresholds (`<= 24h` / `24–48h` / `> 48h`).
   - For rclone reachability, if `rclone about` fails, probe `rclone lsjson --max-depth 1` / `rclone lsd` before reporting unreachable.

## Risks / Trade-offs

- Operators with existing rclone-only `archive-install` setups who rely on `iqoqo-glacier:iqoqo-archive` without setting `RCLONE_REMOTE_ARCHIVE`: mitigated by keeping `iqoqo-glacier:iqoqo-archive` as the default target inside the `rclone` branch of `cloud_backup.sh --archive` and `cloud_backup_cron.sh archive-install`.
