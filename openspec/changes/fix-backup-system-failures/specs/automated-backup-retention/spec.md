## MODIFIED Requirements

### Requirement: Automated Backup Rotation and Archival

The system MUST enforce a backup retention policy that keeps 7 daily and 5 weekly backups in fast storage (Dropbox) and transitions older backups (monthly, quarterly, yearly) to cold storage (AWS S3 Glacier). The retention task MUST coordinate with the backup execution lock to prevent conflicts when both operations run concurrently.

#### Scenario: Running the daily retention task

- **WHEN** the daily backup retention scheduled task executes
- **THEN** the system SHALL check if a backup operation is currently running by attempting to acquire the backup lock
- **THEN** if the lock is held by an active backup, the retention task SHALL exit gracefully without performing any operations
- **THEN** if the lock is available, the system SHALL acquire the lock and proceed with retention operations
- **THEN** the system evaluates existing backups in Dropbox
- **THEN** backups exceeding the 7-daily or 5-weekly limits are uploaded to AWS S3 Glacier
- **THEN** the successfully archived backups are deleted from Dropbox to free up space
- **THEN** the lock SHALL be released when the retention task completes

#### Scenario: Retention task detects active backup

- **WHEN** the daily backup retention scheduled task executes
- **AND** a backup operation is currently running (lock is held)
- **THEN** the retention task SHALL log a message indicating it is skipping execution due to active backup
- **THEN** the retention task SHALL exit with success code (0) without error
- **THEN** the next scheduled retention run SHALL attempt the operation again
