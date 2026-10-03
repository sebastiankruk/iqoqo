## Purpose

Retires the in-container backup rotation requirement. The code it described was
**already unreachable** before `devops-infrastructure-updates` touched it, and is
now removed rather than migrated.

## REMOVED Requirements

### Requirement: Automated Backup Rotation and Archival

Removed. `BackupManager` and the `rotate_and_archive_backups` Celery task have
been deleted.

They were dead code before this change, for three independent reasons:

- the task is **not in `beat_schedule`** (only `refresh-taxonomies-hourly` is), so
  nothing ever triggered it;
- it read `/data/backups`, which is **not mounted** by any compose file;
- `list_backups()` returns `[]` for a missing directory, so even a manual trigger
  was a silent no-op.

The specification had been asserting a retention policy that no deployment
enforced. Off-site archiving is a **host-side** concern, handled by
`scripts/cloud_backup.sh` and its cron installer, and it continues to work: the
host has its own rclone install, and can also use an S3 backend.

#### Scenario: No in-container rotation task exists

- **WHEN** the application is inspected for a backup retention task
- **THEN** no such task SHALL be registered
- **AND** no application code SHALL read or write `/data/backups`

#### Scenario: Host-side archiving still runs

- **WHEN** `scripts/cloud_backup_cron.sh install` has been run
- **THEN** backups SHALL be produced and uploaded nightly by the host scripts
- **AND** the local archive SHALL be deleted only after the upload is confirmed

#### Scenario: An upload failure never destroys the last copy

- **WHEN** the remote upload fails
- **THEN** the local archive SHALL be preserved
- **AND** the script SHALL exit non-zero so the failure is visible to cron

#### Scenario: A half-configured destination stops the run

- **WHEN** no destination is configured at all
- **THEN** the script SHALL abort before starting a database dump
- **AND** it SHALL name both acceptable configurations: `rclone config`, or
  `S3_BUCKET_BACKUP` with `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
