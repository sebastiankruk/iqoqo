# backup-execution-locking Specification

## Purpose

Defines non-reentrant flock-based backup execution locking, timeout wait behavior, and crash safety.

## Requirements

### Requirement: Exclusive backup execution via file locking

The backup script SHALL acquire an exclusive lock before beginning any backup operations to prevent concurrent execution of multiple backup instances.

#### Scenario: Successful lock acquisition

- **WHEN** the backup script starts execution
- **THEN** the script SHALL acquire an exclusive lock on the configured lock file using `flock`, waiting up to `BACKUP_LOCK_TIMEOUT` for a held lock rather than failing on first contact
- **THEN** if lock acquisition succeeds, the script SHALL proceed with backup operations
- **THEN** the lock SHALL be automatically released when the script exits, whether normally, by error, or by signal

#### Scenario: Lock held for longer than the wait ceiling

- **WHEN** the backup script starts execution and cannot acquire the lock within `BACKUP_LOCK_TIMEOUT`
- **THEN** the script SHALL log that another backup is already running, naming the lock path
- **THEN** the script SHALL NOT perform any backup operations
- **THEN** the script SHALL leave the held lock entirely undisturbed

### Requirement: Lock wait ceiling and crash recovery without staleness

The backup script SHALL treat `BACKUP_LOCK_TIMEOUT` as the maximum duration a contending invocation will wait for the lock, and SHALL NOT use it, or the lock file's age, to decide whether a held lock is abandoned. The operating system's `flock` releases a lock when the holding process terminates for any reason, so a crashed backup never requires manual cleanup and a live backup is never displaced.

#### Scenario: Contender waits, then acquires after the holder finishes

- **WHEN** a backup invocation finds the lock held and the holder completes normally within the timeout
- **THEN** the contending invocation SHALL acquire the lock once the holder releases it
- **THEN** the contending invocation SHALL proceed with its own backup
- **AND** the total wait SHALL NOT exceed `BACKUP_LOCK_TIMEOUT`

#### Scenario: Contender gives up without disturbing the holder

- **WHEN** a backup invocation finds the lock held and the holder has not released it when `BACKUP_LOCK_TIMEOUT` elapses
- **THEN** the script SHALL exit with a dedicated lock-contention exit code, distinct from a general failure
- **THEN** the script SHALL log a message naming the lock file path and stating that another backup is running
- **THEN** the script SHALL NOT delete, truncate, or modify the lock file, because the holding process is alive and still holds the lock
- **THEN** the script SHALL NOT perform any dump or upload

#### Scenario: Lock survives a forcibly killed holder

- **WHEN** a backup process is terminated forcibly while holding the lock
- **AND** a subsequent invocation starts
- **THEN** the subsequent invocation SHALL acquire the lock without any manual removal of the lock file
- **THEN** no code path SHALL inspect the lock file's modification time to decide whether to reclaim it

### Requirement: Lock file path configuration

The backup script SHALL support configurable lock file location via environment variable.

#### Scenario: Custom lock file path

- **WHEN** the `BACKUP_LOCK_FILE` environment variable is set
- **THEN** the script SHALL use the specified path for the lock file
- **THEN** the script SHALL create parent directories if they do not exist

#### Scenario: Default lock file path

- **WHEN** the `BACKUP_LOCK_FILE` environment variable is not set
- **THEN** the script SHALL use `/tmp/iqoqo_backup.lock` as the default lock file path
- **THEN** the script SHALL create the lock file with permissions that do not allow another local user to write to it
