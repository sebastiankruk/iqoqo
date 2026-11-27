## 1. S3 Service & Env Configuration (`app/core/s3_service.py`, `.env.example`)

- [x] 1.1 Add optional `storage_class: str | None = None` parameter to `S3Service.upload_file()` in `app/core/s3_service.py` so `ExtraArgs["StorageClass"]` is included when configured
- [x] 1.2 Document `S3_BUCKET_ARCHIVE`, `S3_ARCHIVE_PREFIX`, and `S3_ARCHIVE_STORAGE_CLASS` in `.env.example`

## 2. Backup, Cron, Health Check & Makefile Repair (`scripts/`, `Makefile`)

- [x] 2.1 Update `Makefile` (`archive-run`, `archive-check`) so `iqoqo-glacier:iqoqo-archive` is no longer unconditionally passed as `$1` and `--archive` is passed cleanly
- [x] 2.2 Add `--archive` flag handling in `scripts/cloud_backup.sh`, resolve `S3_BUCKET_ARCHIVE:-S3_BUCKET_BACKUP`, `S3_ARCHIVE_PREFIX` (`archives/`), and `S3_ARCHIVE_STORAGE_CLASS`, and switch upload client construction to `S3Service.from_environment("backup")`
- [x] 2.3 Update `scripts/cloud_backup_cron.sh` (`archive-install`) to emit `./scripts/cloud_backup.sh --archive` and keep S3-mode arguments clean
- [x] 2.4 Update `scripts/cloud_backup_check.sh --archive` to probe `S3_BUCKET_ARCHIVE:-S3_BUCKET_BACKUP` + `S3_ARCHIVE_PREFIX` with monthly freshness thresholds and `rclone about` fallback for S3/Glacier remotes

## 3. Tests & Verification

- [x] 3.1 Add Pytest unit tests in `tests/test_s3_service.py` covering `upload_file(..., storage_class=...)` and `S3Service.from_environment`
- [x] 3.2 Add BATS tests in `tests/bash/` covering `cloud_backup.sh --archive`, `cloud_backup_cron.sh archive-install`, `cloud_backup_check.sh --archive`, and `Makefile` `archive-run` without rclone hijack
- [x] 3.3 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, and `IQOQO_AI_MODE=1 make secret-scan`
