## Context

In-container `rclone` was already retired in v0.8.4 in favor of `app/core/s3_service.py` (`boto3`) so untrusted application containers never mount `~/.config/rclone/rclone.conf`. On the host, `scripts/cloud_backup.sh` intentionally implements a dual-backend architecture (`S3_BACKEND=auto|rclone|s3`):
- `rclone` reaches 40+ consumer and home-lab backends (Dropbox, Google Drive, OneDrive, Nextcloud/WebDAV, SFTP, Backblaze B2).
- `s3` (`boto3` via `app/core/s3_service.py`) streams archives directly to S3-compatible buckets (AWS S3, Cloudflare R2, MinIO, Wasabi, OCI Object Storage) using `.env` credentials.

However, `scripts/cloud_backup.sh` currently archives only `ASSET_PATHS=("app/static/covers" "app/static/gallery" "app/static/uploads/raw_covers")` and omits `data/federation_keys` (`server.pem`, the instance actor RSA private key introduced in v0.9.3 `C87d`). Without `data/federation_keys` in the backup tarball, a restored instance regenerates a new instance key and breaks HTTP Signature verification (`key_fingerprint` pinning) with existing ActivityPub peers.

## Goals / Non-Goals

**Goals:**
- Preserve the `S3_BACKEND=auto|rclone|s3` dual-backend architecture in `scripts/cloud_backup.sh` so both consumer cloud (`rclone`) and enterprise object storage (`s3`) remain supported.
- Add `data/federation_keys` to `ASSET_PATHS` in `scripts/cloud_backup.sh` and restore extraction in `scripts/restore.sh` with strict owner-only permissions (`0700` dir / `0600` key).
- Verify `federation` schema dump and `data/federation_keys` archive/restore in `tests/bash/cloud_backup.bats` and `docs/BACKUPS.md`.

**Non-Goals:**
- Removing `rclone` support from host-side `scripts/cloud_backup.sh`.
- Multi-cloud concurrent replication.

## Decisions

### Retain Host Dual-Backend (`rclone` + Native `boto3` S3)
* **Decision**: Keep `S3_BACKEND=auto|rclone|s3` in `scripts/cloud_backup.sh` rather than retiring host `rclone`.
* **Rationale**: Removing `rclone` from the host script would lock out self-hosters and collectors who rely on Dropbox, Google Drive, OneDrive, WebDAV, or SFTP NAS targets, while offering zero container security benefit since `rclone.conf` is already unmounted from Docker containers.

### Archive and Restore `data/federation_keys`
* **Decision**: Include `data/federation_keys` in `ASSET_PATHS` in `scripts/cloud_backup.sh` and enforce `chmod 0700 data/federation_keys` and `chmod 0600 data/federation_keys/*.pem` during `scripts/restore.sh`.
* **Rationale**: Preserves instance actor cryptographic identity (`server.pem`) across disaster recovery alongside the `pg_dumpall` database dump (`federation.actors` Fernet-encrypted user keys).

## Risks / Trade-offs

- **`[Risk]` Restored `server.pem` file permissions too permissive** -> **Mitigation**: `scripts/cloud_backup.sh` already runs under `umask 077`, and `scripts/restore.sh` explicitly enforces `0700`/`0600` on `data/federation_keys`.
