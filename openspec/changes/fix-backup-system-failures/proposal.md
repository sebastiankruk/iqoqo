## Why

The automated daily backup system has been failing intermittently since September 8th, 2026, with PostgreSQL authentication errors and duplicate script execution. This critical infrastructure issue has resulted in only 7 successful backups over the past 2+ months (last successful: Sep 16), leaving the system without reliable data protection for over 2 weeks. The backup script encounters `role "iqoqo" does not exist` errors despite the role existing, and executes twice per cron invocation, indicating fundamental reliability issues that must be resolved immediately.

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

- `backup-execution-locking`: File-based locking mechanism using flock to ensure only one backup instance runs at a time, with stale lock cleanup after 2-hour timeout
- `backup-database-resilience`: Pre-flight database connectivity verification, role existence checks, and retry logic with exponential backoff for transient connection failures

### Modified Capabilities

- `automated-backup-retention`: Backup retention logic must be aware of locking mechanism to avoid conflicts when cleanup tasks run concurrently with backup operations

## Impact

**Affected Code:**

- `scripts/cloud_backup.sh` - Major refactoring to add locking, retry logic, and enhanced error handling (92 lines → ~180 lines)
- `scripts/cloud_backup_check.sh` - Add duplicate cron detection and lock file validation checks
- `tests/bash/cloud_backup.bats` - Update existing tests and add new tests for locking and retry behavior
- `tests/bash/cloud_backup_check.bats` - Add tests for new validation checks

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
