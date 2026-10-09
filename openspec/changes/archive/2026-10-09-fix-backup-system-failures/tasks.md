> **Re-planned 2026-10-01.** Every task below was written against a 92-line `cloud_backup.sh` that no longer exists — it is 320 lines after the C17 rework, with `S3_BACKEND=auto|rclone|s3` resolution and 58 existing bats tests across three files that must keep passing. Two corrections are baked in: **no mtime-based stale-lock detection** (the kernel releases a `flock` when the holder dies, so it is unnecessary, and it can evict a *live* lock), and the role check must resolve `POSTGRES_USER` rather than hardcoding `iqoqo`. Read the current script before starting; do not refactor sections you are not adding to.

## 1. Execution Locking Infrastructure

- [x] 1.1 Add blocking lock acquisition using `flock -w "${BACKUP_LOCK_TIMEOUT}"` at script start, opening the lock file for writing and holding the descriptor for the process lifetime. Do **not** use `flock -n`
- [x] 1.2 Add `BACKUP_LOCK_FILE` support with default `/tmp/iqoqo_backup.lock`, creating parent directories if needed. ⚠️ Note `/tmp` is on the root filesystem on this host (not tmpfs), so it survives reboot but is shared with any other local user — confirm the mode is not world-writable
- [x] 1.3 Add `BACKUP_LOCK_TIMEOUT` support as a **wait ceiling in seconds** (how long a second invocation blocks before giving up), defaulting to a value with headroom over observed duration (~113 MB archive completes well inside 30 minutes). It is **not** a stale-lock age
- [x] 1.4 On acquisition timeout, exit with code 2 and a message naming the lock file and that another backup is running. **Do not delete or truncate the lock file** — the holder is alive and its lock must not be disturbed
- [x] 1.5 Verify the lock is released on every exit path including `SIGINT`/`SIGTERM`, and add a bats assertion that a crashed-then-rerun invocation acquires the lock immediately without any manual cleanup (proving kernel release, so no staleness logic is needed)
- [x] 1.6 Confirm no mtime-based stale detection is introduced anywhere; if any code path inspects lock age, it is a bug

## 2. Database Pre-flight Checks

- [x] 2.1 Add database container status verification before connection attempts
- [x] 2.2 Implement connectivity test query (SELECT 1) with error capture
- [x] 2.3 Add PostgreSQL role existence verification against `pg_roles`, resolving the role from `${POSTGRES_USER:-iqoqo}` — the same expression `cloud_backup.sh:198` passes to `pg_dumpall`. ⚠️ Never hardcode `iqoqo`: a literal check passes on a stock install and fails on any deployment that renamed the role, which is the misleading diagnosis this change exists to remove
- [x] 2.4 Implement immediate failure for permanent errors (role not found, auth failure), with no retry
- [x] 2.5 Add clear error messages distinguishing transient from permanent failures, including the resolved role name and the effective `POSTGRES_USER` value

## 3. Retry Logic with Exponential Backoff

- [x] 3.1 Implement a retry loop around the **pre-flight checks only**. ⚠️ Do not wrap `pg_dumpall` itself: retrying a multi-gigabyte dump re-does all the work, and the design's stated rationale is that separating connection failure from dump failure lets retry target the former
- [x] 3.2 Add exponential backoff delays (5s, 10s, 20s) between retry attempts
- [x] 3.3 Add `BACKUP_RETRY_ATTEMPTS` environment variable support
- [x] 3.4 Add `BACKUP_RETRY_DELAY_BASE` environment variable support
- [x] 3.5 Implement retry logging with attempt number and delay information
- [x] 3.6 Add comprehensive error reporting after all retries are exhausted
- [x] 3.7 Keep the existing empty-dump guard (`cloud_backup.sh:209`, which fails a zero-exit `pg_dumpall` that produced an empty file) **outside** the retry loop. An empty dump is a permanent failure, not a transient one, and must not be retried as though it were a connection fault

## 4. Enhanced Logging and Error Handling

- [x] 4.1 Create a `log()` helper with ISO 8601 timestamps
- [x] 4.2 Route the script's new and error-path output through `log()`. ⚠️ **Do not convert every existing `echo`** — the current script's emoji-prefixed output is asserted by 24 existing bats tests, and rewriting it wholesale will break them for no functional gain. Add logging; do not reformat
- [x] 4.3 Add a trap-based cleanup handler for temporary files (`BACKUP_DIR`, `ARCHIVE`). Note `trap cleanup EXIT` is also what guarantees the `flock` descriptor closes on abnormal exit
- [x] 4.4 Standardise exit codes: 0 success, 1 general error, 2 lock contention. Check no existing caller depends on the current code for a different meaning
- [x] 4.5 Add an execution summary at completion (success/failure with destination, duration, archive size)
- [x] 4.6 Log the resolved backend and remote (`rclone <remote>` vs `s3 <bucket>`) at start. The C17 rework introduced this resolution, and a failure after it is opaque without knowing which branch ran

## 5. Backup Check Script Enhancements

`cloud_backup_check.sh` is 267 lines with 21 existing bats tests from C17, including the check that the health check can never pass for a destination the nightly job is not writing to. Preserve all of it.

- [x] 5.1 Add duplicate cron entry detection, checking both the crontab and any `cloud_backup_cron.sh`-installed entry
- [x] 5.2 Add lock file validation reporting (path, mode, whether currently held). ⚠️ Report **held or free**, never "stale" — there is no staleness concept in this design
- [x] 5.3 Add validation that `BACKUP_LOCK_TIMEOUT` and `BACKUP_RETRY_ATTEMPTS` are present and parse as positive integers
- [x] 5.4 Verify the new lock and retry env vars are documented in `.env.example` alongside the existing `RCLONE_REMOTE_FAST` and `S3_BACKEND` blocks

## 6. Test Coverage

Baseline to preserve: `cloud_backup.bats` 24 tests, `cloud_backup_cron.bats` 13, `cloud_backup_check.bats` 21. All 58 must pass unchanged at the end of this change.

- [x] 6.1 Add locking tests to `tests/bash/cloud_backup.bats` — acquire-and-release on success, and lock contention producing exit 2
- [x] 6.2 Add a contention test that runs two invocations concurrently and asserts exactly one performs a dump and upload
- [x] 6.3 Add a crash-recovery test: start an invocation, `kill -9` it, then assert a fresh invocation acquires the lock with no manual cleanup. This is the test that **proves no staleness logic is needed**, and it fails if anyone reintroduces mtime handling
- [x] 6.4 Add a test asserting the lock file is **not** deleted by a waiter that times out
- [x] 6.5 Add pre-flight check tests: container down, `SELECT 1` failing, and role absent
- [x] 6.6 Add a role-rename test — set `POSTGRES_USER` to a non-default value and assert the existence check follows it. This is the regression guard for task 2.3
- [x] 6.7 Add retry tests with simulated transient failures, asserting the 5s/10s/20s schedule (use a stubbed sleep so the suite does not actually wait 35s)
- [x] 6.8 Add permanent-failure tests asserting **no** retry on auth failure and on missing role
- [x] 6.9 Add a test that an empty dump is **not** retried (task 3.7)
- [x] 6.10 Add cleanup-handler tests across exit paths, including signal interruption
- [x] 6.11 Add the corresponding validation tests to `cloud_backup_check.bats`
- [x] 6.12 Run all three suites and confirm 58 existing tests plus the new ones pass

## 7. Integration Testing and Validation

- [x] 7.1 Run a real backup end to end and confirm the archive is non-empty and reaches the configured destination
- [x] 7.2 Trigger two parallel invocations and confirm one backs up and the other exits 2 without corrupting the archive
- [x] 7.3 Stop the database container mid-preflight and confirm the retry ladder runs and then reports clearly
- [x] 7.4 Verify log output for every path: success, lock contention, transient exhausted, permanent failure
- [x] 7.5 Confirm no orphaned temp files after both success and failure
- [x] 7.6 Run `cloud_backup_check.sh` against healthy and each failure configuration

## 8. Documentation

- [x] 8.1 Update the script header comment block with the new environment variables, keeping the C17 backend-resolution documentation intact
- [x] 8.2 Add a troubleshooting section covering: lock contention (exit 2), permanent vs transient failure, and the meaning of each new exit code
- [x] 8.3 Document that `BACKUP_LOCK_TIMEOUT` is a **wait ceiling, not a stale-lock age** — the previous design's meaning was the opposite and is the kind of documentation error that produces a lock deleted mid-backup
- [x] 8.4 Document the deliberate absence of retention: nothing on the host deletes old archives, S3-side lifecycle rules own that after the Dropbox→S3 migration, and until then the destination grows unbounded
- [x] 8.5 Update `docs/BACKUPS.md` §1 (fast backups) to mention locking and retry. ⚠️ Do **not** touch §2 (archive), §3 (covers) or §4 (feedback) — those remotes are out of scope, and §3/§4 are being changed by `feedback-screenshot-storage-retirement` in v0.8.3
