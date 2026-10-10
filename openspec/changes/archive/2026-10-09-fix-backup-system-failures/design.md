## Context

The host-side daily cron job at 03:00 executes `scripts/cloud_backup.sh`, which performs a `pg_dumpall`, compresses the asset volumes, and uploads to cloud storage. A separate monthly cron invokes the same script against a cold remote for long-term archival.

> **Corrected 2026-10-01.** This context originally opened with the backup system "experiencing intermittent failures since September 8th", citing `role "iqoqo" does not exist` errors and duplicate execution as the cause of "only 7 successful backups over 2+ months". **That is not the current state and no task should be written against it.** Verified: archives exist for 2026-09-27, 2026-09-30 and 2026-10-01 from the same cron entry; `pg_dumpall -c -U iqoqo` exits 0; the role resolves. The script *does* still contain a `POSTGRES_USER:-iqoqo` fallback, so the reported error is possible under a renamed role — see Decision 3 — but it is not happening here and must be substantiated before being chased.

The gaps that are real, confirmed by reading the current 320-line script:

1. **No locking at all**: no `flock`, and no protection against a double cron trigger
2. **No retry**: no retry or backoff on any transient failure
3. **No pre-flight verification**: the script goes straight to `pg_dumpall`, so a connection failure is indistinguishable from a misconfiguration
4. **Minimal error context**: failures surface as a single line with no attempt count or classification

Stakeholders: System administrators, data protection compliance, end users relying on data integrity.

## Goals / Non-Goals

**Goals:**

- Eliminate duplicate backup execution through file-based locking
- Achieve >95% backup success rate through retry logic and pre-flight checks
- Provide clear, actionable error messages for different failure modes
- Ensure cleanup of temporary files on all exit paths (success and failure)
- Maintain backward compatibility with existing cron configuration and rclone setup
- Add comprehensive test coverage for new locking and retry behaviors
- Preserve every behaviour the C17 rework established: the `S3_BACKEND=auto|rclone|s3` resolution, the empty-dump guard, `ASSET_PATHS`, and the existing 58 bats tests

**Non-Goals:**

- Changing the backup schedule, and **implementing retention** (delegated to S3-side lifecycle rules — see proposal "Scope decisions")
- Changing the cloud storage destination, the rclone configuration, or the rclone/boto3 split between host and container
- Modifying backend selection or the `S3_BUCKET_BACKUP` contract that `cloud_backup.sh` already reads
- Implementing backup encryption (already handled by the cloud provider, and `S3_SSE` for the S3 backend)
- Adding backup restore functionality (out of scope for this fix)
- Migrating to a different backup tool or framework
- Changing the database container orchestration (Docker Compose setup remains unchanged)
- Removing feedback screenshot storage from the container (that is `feedback-screenshot-storage-retirement`, v0.8.3)

## Decisions

### Decision 1: File-based locking with flock (REVISED 2026-10-01)

> **The original design was self-defeating and has been replaced.** It specified `flock -n` (non-blocking) *and* mtime-based stale-lock detection. These cannot both work: with `-n`, a genuinely held lock is never inspected and never classified as stale, so the stale-detection branch is unreachable for the case it exists to handle. Meanwhile a lock file left behind by a crashed process still *looks* old by mtime while holding no lock at all, so the branch is only reachable for the one case where removing it is unnecessary.

**Choice**: `flock` with a **bounded blocking** acquisition (`-w <timeout>`), and no mtime-based staleness at all.

**Rationale**:

- `flock` is part of util-linux (standard on all Linux distributions), requiring no additional dependencies
- Provides kernel-level atomic locking, preventing race conditions
- **The kernel releases the lock when the holding process dies**, for any reason including `SIGKILL`. Crash cleanup is therefore already correct and needs no separate mechanism — which is precisely why mtime staleness is unnecessary.
- Blocking-with-timeout is the only mode that gets both properties at once: a live holder is waited for (bounded), and a dead holder is acquired immediately because the kernel has already freed it.
- Alternative considered: mtime-based stale detection. **Rejected** — it can evict a *live* lock held by a backup exceeding the threshold, which would reintroduce the exact double-execution this change exists to prevent.
- Alternative considered: PID-based locking. Rejected as more complex, requiring signal handling, and prone to PID reuse.
- Alternative considered: Database-based locking. Rejected: adds complexity and requires the database connection that may itself be the failing component.

**Implementation**: Lock file at `${BACKUP_LOCK_FILE:-/tmp/iqoqo_backup.lock}`, acquired with `flock -w "${BACKUP_LOCK_TIMEOUT}"`. On timeout, exit with a distinct code (2) and a message naming the holder; do not delete the lock file, because the holder is alive. The lock is released automatically on every exit path, including signals — no trap needed for the lock itself, only for temporary-file cleanup.

> `BACKUP_LOCK_TIMEOUT` no longer means "age at which a lock is presumed abandoned". It is now a **wait ceiling**: how long a second invocation will block before giving up. The default should reflect a realistic backup duration (observed: a ~113 MB archive completes well inside 30 minutes) with headroom.

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

> **Correction (2026-10-01).** Step 3 hardcodes `'iqoqo'`, but the role is operator-configurable: `cloud_backup.sh:198` already passes `-U '${POSTGRES_USER:-iqoqo}'`, and `docker-compose.yml:143` defines `POSTGRES_USER=${POSTGRES_USER:-iqoqo}`. A check against a literal `iqoqo` would **pass on a stock install and fail on any deployment that renamed the role**, producing exactly the misleading diagnosis this change exists to eliminate. The existence check must resolve the role from `POSTGRES_USER` with the same fallback, and the two must not be allowed to drift.

> Also note the current script already contains a correct guard worth preserving rather than rewriting: `cloud_backup.sh:209` treats a zero-exit `pg_dumpall` that produced an empty file as a **failure** ("a `pg_dumpall` exiting 0 doesn't guarantee non-empty"). Any retry work must keep that check outside the retry loop, so an empty dump is not retried as if it were a connection failure.

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
→ **Mitigation**: Lock file is specific to this script path; a manual backup can use a different lock file via `BACKUP_LOCK_FILE` (future enhancement: a `--no-lock` flag). Current use case has only one backup source (cron).

**Risk**: A wait ceiling set too low turns a slow-but-healthy backup into a spurious failure for the waiter
→ **Mitigation**: The ceiling is configurable via `BACKUP_LOCK_TIMEOUT` and now means "how long to wait", not "how old is stale". Default it against observed duration (a ~113 MB archive completes well inside 30 minutes) with headroom. A waiter that times out exits 2 without touching the lock file, so the holder is never disturbed. The failure mode is a logged, retryable "another backup is running", which is the correct signal.

**Risk**: Retry logic masks persistent database configuration issues
→ **Mitigation**: Retry only applies to transient connection failures. Persistent issues (role doesn't exist, wrong credentials) fail immediately without retry. Log clearly distinguishes transient vs permanent failures.

**Risk**: Pre-flight checks add overhead to every backup execution
→ **Mitigation**: Pre-flight checks are lightweight (single SQL query each). Total overhead <1 second. Benefit of early failure detection outweighs minimal time cost.

**Risk**: Changes to backup script may introduce regressions
→ **Mitigation**: Comprehensive test coverage with bats. **The existing suite is substantial — 24 tests in `cloud_backup.bats`, 21 in `cloud_backup_check.bats`, 13 in `cloud_backup_cron.bats`, all written by the C17 rework — and every one must still pass unchanged.** New tests cover locking, retry, and error handling. Treat any pre-existing failure as a blocker, not a known issue.

**Risk**: The original change was written against a 92-line script; the real one is 320 lines and already carries the backend-resolution logic
→ **Mitigation**: Read the current script before estimating, and budget additions against it. The original "92 → ~180 lines" framing is void. Anything that reorders or rewrites existing sections for tidiness is out of scope — add, do not refactor.

**Trade-off**: Increased script complexity (320 → ~420 lines) for improved reliability
→ **Justification**: Backup reliability is critical for data protection. Additional complexity is isolated to backup scripts, well-tested, and provides significant operational benefits.

**Trade-off**: Lock file introduces single point of failure for backup execution
→ **Justification**: Lock file failures are rare (filesystem issues). Failure mode is safe (backup doesn't run, alert generated). Alternative (no locking) has worse failure mode (duplicate backups, resource contention, potential data corruption).
