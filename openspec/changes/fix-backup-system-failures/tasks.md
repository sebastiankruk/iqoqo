## 1. Execution Locking Infrastructure

- [ ] 1.1 Add lock file acquisition logic using flock at script start
- [ ] 1.2 Implement stale lock detection based on file modification time (2-hour default timeout)
- [ ] 1.3 Add BACKUP_LOCK_FILE environment variable support for custom lock path
- [ ] 1.4 Add BACKUP_LOCK_TIMEOUT environment variable support for custom timeout
- [ ] 1.5 Implement lock acquisition failure handling with clear error message
- [ ] 1.6 Add trap-based cleanup to ensure lock release on all exit paths

## 2. Database Pre-flight Checks

- [ ] 2.1 Add database container status verification before connection attempts
- [ ] 2.2 Implement connectivity test query (SELECT 1) with error capture
- [ ] 2.3 Add PostgreSQL role existence verification query against pg_roles
- [ ] 2.4 Implement immediate failure for permanent errors (role not found, auth failure)
- [ ] 2.5 Add clear error messages distinguishing transient vs permanent failures

## 3. Retry Logic with Exponential Backoff

- [ ] 3.1 Implement retry loop wrapper for database connectivity checks
- [ ] 3.2 Add exponential backoff delays (5s, 10s, 20s) between retry attempts
- [ ] 3.3 Add BACKUP_RETRY_ATTEMPTS environment variable support
- [ ] 3.4 Add BACKUP_RETRY_DELAY_BASE environment variable support
- [ ] 3.5 Implement retry logging with attempt number and delay information
- [ ] 3.6 Add comprehensive error reporting after all retries exhausted

## 4. Enhanced Logging and Error Handling

- [ ] 4.1 Create log() helper function with ISO 8601 timestamps
- [ ] 4.2 Convert all echo statements to use log() function with appropriate emoji indicators
- [ ] 4.3 Add trap-based cleanup handler for temporary files (BACKUP_DIR and ARCHIVE)
- [ ] 4.4 Implement exit code standardization (0=success, 1=general error, 2=lock error)
- [ ] 4.5 Add execution summary report at script completion (success/failure with details)
- [ ] 4.6 Log the exact docker exec command being executed for debugging

## 5. Backup Check Script Enhancements

- [ ] 5.1 Add duplicate cron entry detection in cloud_backup_check.sh
- [ ] 5.2 Add lock file validation check (existence, permissions, staleness)
- [ ] 5.3 Add database connectivity pre-flight check validation
- [ ] 5.4 Update check script to verify retry configuration environment variables

## 6. Test Coverage

- [ ] 6.1 Update tests/bash/cloud_backup.bats for new locking behavior
- [ ] 6.2 Add tests for successful lock acquisition and release
- [ ] 6.3 Add tests for lock contention (concurrent execution prevention)
- [ ] 6.4 Add tests for stale lock detection and cleanup
- [ ] 6.5 Add tests for database connectivity pre-flight checks
- [ ] 6.6 Add tests for retry logic with simulated transient failures
- [ ] 6.7 Add tests for permanent failure handling (no retry on auth errors)
- [ ] 6.8 Add tests for cleanup handler on various exit paths
- [ ] 6.9 Update tests/bash/cloud_backup_check.bats for new validation checks

## 7. Integration Testing and Validation

- [ ] 7.1 Perform manual backup execution to verify end-to-end functionality
- [ ] 7.2 Test concurrent execution prevention with parallel script invocations
- [ ] 7.3 Test retry logic with simulated database unavailability
- [ ] 7.4 Verify log output format and content for all scenarios
- [ ] 7.5 Validate cleanup behavior on successful and failed backups
- [ ] 7.6 Test backup check script with various failure scenarios

## 8. Documentation

- [ ] 8.1 Update script header comments with new environment variables
- [ ] 8.2 Add troubleshooting section for common failure modes
- [ ] 8.3 Document lock file location and timeout configuration
- [ ] 8.4 Update README or operational docs with new backup behavior
