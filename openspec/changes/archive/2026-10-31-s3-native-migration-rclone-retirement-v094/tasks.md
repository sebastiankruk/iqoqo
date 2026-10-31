## 1. Dual-Backend Backup & Federation Key Preservation

- [x] 1.1 Preserve `S3_BACKEND=auto|rclone|s3` dual-backend support in `scripts/cloud_backup.sh` and add `data/federation_keys` (`server.pem`) to `ASSET_PATHS`.
- [x] 1.2 Update `scripts/restore.sh` to restore `data/federation_keys` with strict `0700`/`0600` permissions alongside the full `pg_dumpall` (`federation` schema) restore.

## 2. BATS Testing & Documentation

- [x] 2.1 Update `tests/bash/cloud_backup.bats` to verify `data/federation_keys` archive inclusion while testing both `rclone` and `s3` backend paths.
- [x] 2.2 Update `docs/BACKUPS.md` and `.context/notes/plan/0.9.x-release-plan.md` to document dual-backend (`rclone` + native S3) federation key backup and restore.

