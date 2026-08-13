# automated-backup-retention Specification

## Purpose

TBD - created by archiving change devops-sre-backup-hardening. Update Purpose after archive.

## Requirements

### Requirement: Automated Backup Rotation and Archival

The system MUST enforce a backup retention policy that keeps 7 daily and 5 weekly backups in fast storage (Dropbox) and transitions older backups (monthly, quarterly, yearly) to cold storage (AWS S3 Glacier).

#### Scenario: Running the daily retention task

- **WHEN** the daily backup retention scheduled task executes
- **THEN** the system evaluates existing backups in Dropbox
- **THEN** backups exceeding the 7-daily or 5-weekly limits are uploaded to AWS S3 Glacier
- **THEN** the successfully archived backups are deleted from Dropbox to free up space
