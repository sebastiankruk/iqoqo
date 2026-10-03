## Why

The host-side backup script has no protection against concurrent execution, no retry on transient database failures, and minimal error context, so a failure is indistinguishable from a misconfiguration and a double cron trigger silently doubles both I/O and provider cost.

> **Corrected 2026-10-01.** This proposal originally claimed the system "has been failing intermittently since September 8th, with only 7 successful backups over the past 2+ months (last successful: Sep 16)" and that the failures must be resolved "immediately". **That claim no longer holds and should not be used to justify scope.** Verified on this host: archives exist for 2026-09-27, 2026-09-30 and 2026-10-01, produced by the same 03:00 cron entry; `pg_dumpall -c -U iqoqo` exits 0 against the running database; and `SELECT rolname FROM pg_roles WHERE rolname='iqoqo'` returns the role. The `role "iqoqo" does not exist` error is **not reproducible** in the current environment, so no task below should be written to chase it without first substantiating it.
>
> The sparse archive history (Jul 8, Aug 4, then a gap to Sep 27) is a real gap, but its cause is not established and predates the work in this change. The 3-day spacing of the recent archives suggests the job is being run selectively rather than failing nightly, which is a different problem with a different owner.

What remains genuinely missing, verified by reading the current script: **no `flock` and no retry or backoff anywhere in `cloud_backup.sh`.** Those two gaps are the substance of this change and are unaffected by the above.

## What Changes

- Add file-based locking mechanism to prevent duplicate backup execution when cron triggers multiple instances
- Implement database connection pre-flight checks with retry logic (3 attempts with exponential backoff: 5s, 10s, 20s)
- Verify PostgreSQL role existence before attempting pg_dumpall to provide clear error messages
- Add comprehensive error handling with timestamped logging for all critical operations
- Implement cleanup handlers to prevent orphaned temporary files on failure
- Add execution summary reporting (success/failure with detailed status)
- Enhance backup check script to detect duplicate cron entries and validate locking behavior

## Capabilities

### New Capabilities

- `backup-execution-locking`: File-based locking via `flock` ensuring only one backup instance runs at a time, using a bounded blocking acquisition rather than mtime-based stale detection (see design Decision 1)
- `backup-database-resilience`: Pre-flight database connectivity verification, role existence checks, and retry logic with exponential backoff for transient connection failures

### Modified Capabilities

None. `automated-backup-retention` was previously listed here and that delta spec has been **deleted** — see "Scope decisions" below.

## Scope decisions (2026-10-01)

Three decisions were taken after reviewing this change against the deployment as it actually exists. They are recorded here so they are not re-litigated during implementation.

**1. Retention is deliberately out of scope.** The original proposal modified `automated-backup-retention` to make retention lock-aware. That capability was **retired from the main specs during the `devops-infrastructure-updates` archive on 2026-09-29** (task 8.1), because it described `BackupManager` and `rotate_and_archive_backups`, which were unreachable in any deployment: no Celery beat entry, `/data/backups` mounted by no compose file, and an empty listing on a missing directory. The spec asserted a 7-daily / 5-weekly / Glacier promotion policy that **nothing ever enforced**. Re-adding it here would resurrect a spec that was deliberately deleted for asserting an unimplemented behaviour.

Retention is instead **delegated to S3-side lifecycle rules**, on the planned migration of the Backup remote from Dropbox to S3. Accepted consequence, stated plainly: until that migration lands, the Dropbox destination grows unbounded at roughly 113 MB/day for the current data size, because nothing on the host deletes old archives. This is a deliberate, time-bounded gap, not an oversight.

**2. Backup and Archive remain host-side and on rclone.** The three storage roles are deliberately asymmetric and this change preserves that:

| Role | Tool | In Docker | Nature |
|---|---|---|---|
| Backup (fast) | rclone | host | write-only, cron 03:00 |
| Archive (cold) | rclone | host | write-only, manual monthly cron |
| Covers (shared cache) | boto3 (`s3_service.py`) | in-container | read-through cache |

rclone stays on the host because it reaches B2, Google Drive, Dropbox, SFTP and Wasabi, which boto3 cannot. The containers use boto3 because mounting a plaintext `rclone.conf` into the process that parses untrusted input is the actual risk. This change touches only the host-side scripts and must not move backup execution into a container.

**3. Feedback screenshots are being removed from object storage in a separate change** (`feedback-screenshot-storage-retirement`, v0.8.3), not here. `ASSET_PATHS` in `cloud_backup.sh` already includes `app/static/gallery`, so the nightly backup already ships screenshots offsite and a second in-container copy buys nothing.

## Impact

**Affected Code:**

- `scripts/cloud_backup.sh` — currently 320 lines; add locking, retry, and structured error handling
- `scripts/cloud_backup_check.sh` — currently 267 lines; add duplicate cron detection and lock file validation
- `tests/bash/cloud_backup.bats` — 24 existing tests to preserve; add locking and retry coverage
- `tests/bash/cloud_backup_check.bats` — 21 existing tests to preserve; add validation coverage
- `tests/bash/cloud_backup_cron.bats` — 13 existing tests; interaction with the cron installer is affected by locking

> The original proposal said `cloud_backup.sh` was 92 lines growing to ~180. It is **320 lines**, because `devops-infrastructure-updates` (C17) already reworked it to add the `S3_BACKEND=auto|rclone|s3` resolution. Budget additions against the real file, not the assumed one.

**Explicitly unchanged:** backend selection (`S3_BACKEND`), the rclone/S3 split, `S3_BUCKET_BACKUP` (still read by this script for the S3 backend — note `cloud_backup.sh` constructs `S3Service("backup")` for its upload, so the `BUCKET_BACKUP` role in `s3_service.py` is live from the host even though no in-container caller uses it), and `ASSET_PATHS`.

**Dependencies:**

- Requires `flock` utility (part of util-linux, standard on Linux systems)
- No new external dependencies; uses existing Docker and PostgreSQL client tools

**Systems:**

- Cron job execution behavior changes (locking prevents concurrent runs)
- Backup logging format changes (timestamped entries, structured error messages)
- Temporary file cleanup behavior (explicit cleanup on failure paths)
- Database connection handling (pre-flight checks before dump operations)

**APIs/Interfaces:**

- No changes to external APIs or user-facing interfaces
- Internal script behavior changes (exit codes, log format, retry behavior)

**Risk Mitigation:**

- Minimal risk: changes are isolated to backup scripts
- Backward compatible: script accepts same arguments and produces same output structure
- Fail-safe: locking mechanism includes timeout to prevent permanent lockouts
