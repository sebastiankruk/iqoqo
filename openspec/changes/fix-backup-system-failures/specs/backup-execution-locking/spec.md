## ADDED Requirements

### Requirement: Exclusive backup execution via file locking

The backup script SHALL acquire an exclusive lock before beginning any backup operations to prevent concurrent execution of multiple backup instances.

#### Scenario: Successful lock acquisition

- **WHEN** the backup script starts execution
- **THEN** the script SHALL attempt to acquire an exclusive lock on `/tmp/iqoqo_backup.lock` using `flock`
- **THEN** if lock acquisition succeeds, the script SHALL proceed with backup operations
- **THEN** the lock SHALL be automatically released when the script exits (normal or abnormal termination)

#### Scenario: Lock already held by another instance

- **WHEN** the backup script starts execution
- **AND** another backup instance already holds the lock
- **THEN** the script SHALL exit immediately with exit code 1
- **THEN** the script SHALL log an error message indicating another backup is already running
- **THEN** the script SHALL NOT perform any backup operations

### Requirement: Stale lock detection and cleanup

The backup script SHALL detect and handle stale lock files that may remain after a crashed or killed backup process.

#### Scenario: Stale lock older than timeout threshold

- **WHEN** the backup script attempts to acquire the lock
- **AND** the lock file exists with modification time older than 2 hours (configurable via `BACKUP_LOCK_TIMEOUT` environment variable)
- **THEN** the script SHALL remove the stale lock file
- **THEN** the script SHALL log a warning message indicating stale lock removal
- **THEN** the script SHALL proceed with lock acquisition

#### Scenario: Lock file within timeout threshold

- **WHEN** the backup script attempts to acquire the lock
- **AND** the lock file exists with modification time newer than the timeout threshold
- **THEN** the script SHALL treat the lock as valid
- **THEN** the script SHALL exit with error indicating another backup is running

### Requirement: Lock file path configuration

The backup script SHALL support configurable lock file location via environment variable.

#### Scenario: Custom lock file path

- **WHEN** the `BACKUP_LOCK_FILE` environment variable is set
- **THEN** the script SHALL use the specified path for the lock file
- **THEN** the script SHALL create parent directories if they do not exist

#### Scenario: Default lock file path

- **WHEN** the `BACKUP_LOCK_FILE` environment variable is not set
- **THEN** the script SHALL use `/tmp/iqoqo_backup.lock` as the default lock file path
