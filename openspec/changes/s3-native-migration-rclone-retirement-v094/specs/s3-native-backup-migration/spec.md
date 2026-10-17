## Purpose
Retire residual rclone dependencies in favor of native S3 service and include federation schema in backups.

## ADDED Requirements

### Requirement: Native S3 Backup Verification

The backup system SHALL back up and verify the entire PostgreSQL database including the federation schema via native S3 APIs.

#### Scenario: Backup includes federation schema
- **WHEN** cloud_backup.sh executes scheduled backup
- **THEN** Database dump contains federation schema and uploads successfully using boto3.

