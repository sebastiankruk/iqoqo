## Context

The iQoQo backup system has been experiencing intermittent failures since September 8th, 2026. The daily cron job at 03:00 executes `scripts/cloud_backup.sh`, which performs PostgreSQL database dumps and asset archival to cloud storage via rclone.

Current issues:

1. **Duplicate execution**: The backup script runs twice per cron invocation, as evidenced by duplicate "Starting iQoQo backup" log entries
2. **Database authentication failures**: `pg_dumpall` fails with `role "iqoqo" does not exist` despite the role existing and manual connections succeeding
3. **Timing correlation**: The database container was recreated on Sep 22 at 03:41 (after the 03:00 backup attempt), suggesting container lifecycle issues affect backup reliability
4. **Insufficient error handling**: Current script lacks retry logic, pre-flight checks, and structured error reporting

The backup script currently has no protection against concurrent execution, no mechanism to handle transient database connection failures, and minimal error context in logs. This has resulted in only 7 successful backups over 2+ months, creating a critical data protection gap.

Stakeholders: System administrators, data protection compliance, end users relying on data integrity.

## Goals / Non-Goals

**Goals:**

- Eliminate duplicate backup execution through file-based locking
- Achieve >95% backup success rate through retry logic and pre-flight checks
- Provide clear, actionable error messages for different failure modes
- Ensure cleanup of temporary files on all exit paths (success and failure)
- Maintain backward compatibility with existing cron configuration and rclone setup
- Add comprehensive test coverage for new locking and retry behaviors

**Non-Goals:**

- Changing the backup schedule or retention policy (separate concern)
- Modifying the cloud storage destination or rclone configuration
- Implementing backup encryption (already handled by cloud provider)
- Adding backup restore functionality (out of scope for this fix)
- Migrating to a different backup tool or framework
- Changing the database container orchestration (Docker Compose setup remains unchanged)

## Decisions

### Decision 1: File-based locking with flock

**Choice**: Use `flock` for exclusive file locking with a 2-hour timeout for stale locks.

**Rationale**:

- `flock` is part of util-linux (standard on all Linux distributions), requiring no additional dependencies
- Provides kernel-level atomic locking, preventing race conditions
- File-based locks persist across process crashes and can be cleaned up
- 2-hour timeout balances between preventing permanent lockouts and allowing long-running backups to complete
- Alternative considered: PID-based locking (more complex, requires signal handling, prone to PID reuse issues)
- Alternative considered: Database-based locking (adds complexity, requires database connection which may be the failing component)

**Implementation**: Lock file at `/tmp/iqoqo_backup.lock` with `flock -n` for non-blocking acquisition. If lock acquisition fails, exit immediately with clear error message. Stale lock detection via file modification time.

### Decision 2: Exponential backoff retry strategy

**Choice**: 3 retry attempts with delays of 5s, 10s, 20s (exponential backoff).

**Rationale**:

- Exponential backoff prevents overwhelming a recovering database with rapid retry attempts
- 3 attempts balances reliability (handles transient failures) with execution time (max 37s additional delay)
- Delays chosen to cover typical container restart times (5-15s) and database recovery periods
- Alternative considered: Fixed 5s delay between retries (less effective for longer recovery scenarios)
- Alternative considered: More retries with longer delays (increases total execution time, may mask persistent issues)

**Implementation**: Retry loop around database connection pre-flight check and pg_dumpall execution. Each retry logs the attempt number and delay. Final failure provides detailed diagnostic information.

### Decision 3: Pre-flight database connectivity verification

**Choice**: Verify database connectivity and role existence before attempting pg_dumpall.

**Rationale**:

- Separates connection failures from dump failures, enabling targeted error messages
- Allows retry logic to focus on connection issues rather than dump execution
- Role existence check provides early detection of configuration drift
- Alternative considered: Rely solely on pg_dumpall exit codes (less granular error information, harder to distinguish transient vs permanent failures)
- Alternative considered: Skip pre-flight and retry pg_dumpall directly (retries entire dump operation, less efficient)

**Implementation**:

1. Check database container is running
2. Attempt `psql` connection with simple query (`SELECT 1`)
3. Verify role exists with `SELECT rolname FROM pg_roles WHERE rolname = 'iqoqo'`
4. Only proceed to pg_dumpall if all checks pass

### Decision 4: Structured logging with timestamps

**Choice**: Add ISO 8601 timestamps to all log entries and use emoji-prefixed status indicators.

**Rationale**:

- Timestamps enable correlation with other system events (container restarts, cron execution)
- Consistent log format simplifies parsing and monitoring
- Emoji indicators provide visual scanning aid in log files
- Alternative considered: JSON structured logging (more complex, requires additional tooling to parse)
- Alternative considered: Syslog integration (adds complexity, not necessary for single-host deployment)

**Implementation**: Helper function `log()` that prepends timestamp and optional emoji. All echo statements converted to use this function.

### Decision 5: Trap-based cleanup on failure

**Choice**: Use bash `trap` to ensure cleanup of temporary files on all exit paths.

**Rationale**:

- Guarantees cleanup even on unexpected errors or signal interruptions
- Prevents accumulation of orphaned temporary files in `/tmp`
- Centralizes cleanup logic rather than duplicating in each error path
- Alternative considered: Explicit cleanup in each error branch (error-prone, easy to miss paths)
- Alternative considered: Rely on system `/tmp` cleanup (unreliable timing, may not happen before next backup)

**Implementation**: `trap cleanup EXIT` at script start. Cleanup function removes `BACKUP_DIR` and `ARCHIVE` if they exist. Lock file released automatically when script exits (flock behavior).

## Risks / Trade-offs

**Risk**: Lock file prevents legitimate concurrent backups from different sources
→ **Mitigation**: Lock file is specific to this script path; manual backups can use different lock file or `--no-lock` flag (future enhancement). Current use case has only one backup source (cron).

**Risk**: 2-hour stale lock timeout may be too aggressive for very large databases
→ **Mitigation**: Timeout is configurable via environment variable `BACKUP_LOCK_TIMEOUT`. Current 2-hour value based on observed backup duration (<30 minutes for current data size). Monitor and adjust if needed.

**Risk**: Retry logic masks persistent database configuration issues
→ **Mitigation**: Retry only applies to transient connection failures. Persistent issues (role doesn't exist, wrong credentials) fail immediately without retry. Log clearly distinguishes transient vs permanent failures.

**Risk**: Pre-flight checks add overhead to every backup execution
→ **Mitigation**: Pre-flight checks are lightweight (single SQL query each). Total overhead <1 second. Benefit of early failure detection outweighs minimal time cost.

**Risk**: Changes to backup script may introduce regressions
→ **Mitigation**: Comprehensive test coverage with bats. Existing test suite validates current behavior. New tests cover locking, retry, and error handling. Manual testing before deployment.

**Trade-off**: Increased script complexity (92 → ~180 lines) for improved reliability
→ **Justification**: Backup reliability is critical for data protection. Additional complexity is isolated to backup scripts, well-tested, and provides significant operational benefits.

**Trade-off**: Lock file introduces single point of failure for backup execution
→ **Justification**: Lock file failures are rare (filesystem issues). Failure mode is safe (backup doesn't run, alert generated). Alternative (no locking) has worse failure mode (duplicate backups, resource contention, potential data corruption).
