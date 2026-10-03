# Design: Fix myKG Background Container SIGINT Cleanup

## Context

In `Makefile`, the `mykg-update` and `mykg-index` targets launch a background container named `mykg-agy-daemon` using `docker compose -f docker-compose.ai_sandbox.yml run --rm -d --name mykg-agy-daemon`. Once launched, Python scripts (`run_update.py` or `run_index.py`) execute in the foreground.

Under normal execution, teardown commands (`docker compose down` and `docker rm -f mykg-agy-daemon`) execute sequentially after the Python script completes. However, if the user sends `SIGINT` (Ctrl+C) or `SIGTERM`, the shell terminates immediately. The sequential teardown commands are bypassed, leaving the container running or stopped in Docker's namespace. Subsequent runs fail with:
`docker: Error response from daemon: Conflict. The container name "/mykg-agy-daemon" is already in use`.

See `proposal.md` for problem motivation and scope.

## Goals / Non-Goals

**Goals:**
- Guarantee execution of container teardown commands upon normal exit or signal interception (`SIGINT`, `SIGTERM`, `EXIT`).
- Enforce pre-flight container eviction to remove any stale or orphan `mykg-agy-daemon` before launching a new one.
- Maintain accurate exit code propagation from `run_update.py` / `run_index.py`.
- Provide automated Bats regression tests in `tests/bash/mykg_tooling.bats` validating signal trapping and collision prevention.

**Non-Goals:**
- Randomized or dynamic container names: `mykg-agy-daemon` relies on a known name for deterministic proxy routing, health checks, and monitoring.
- Altering the internal task polling loop in `agy_daemon.py` (which already handles SIGINT/SIGTERM inside the container).

## Decisions

### Decision 1: POSIX Shell Trap Handler in Makefile
Register a cleanup trap at the start of the shell recipe block in `mykg-update` and `mykg-index`:
```sh
cleanup() {
    EXIT_CODE=$$?;
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        docker compose -f docker-compose.ai_sandbox.yml down >/dev/null 2>&1 || true;
        docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true;
    fi;
    exit $$EXIT_CODE;
};
trap cleanup EXIT INT TERM;
```
*Rationale*: Shell traps in the recipe ensure teardown runs regardless of whether the Python script exits cleanly, crashes, or is terminated by `SIGINT` or `SIGTERM`.
*Alternatives considered*:
- Wrapping cleanup in a Python `atexit` handler inside `run_update.py`/`run_index.py`. Rejected because the container is launched by Make *before* Python starts; if Make is interrupted during container bootstrap or Python invocation, Python handlers cannot run.

### Decision 2: Pre-Flight Container Eviction
Before invoking `docker compose run --rm -d --name mykg-agy-daemon`, invoke `docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true`.
*Rationale*: If a host crash or uncatchable `SIGKILL` previously occurred, an orphaned container might still occupy the name. Pre-flight removal ensures idempotent startup.

### Decision 3: Test Verification via Bats
Add dedicated Bats tests to `tests/bash/mykg_tooling.bats`:
1. Verify `make -n mykg-update` and `make -n mykg-index` contain the trap registration (`trap ... EXIT INT TERM`) and pre-flight cleanup (`docker rm -f mykg-agy-daemon`).
2. Verify simulated SIGINT interruption cleans up container state.

## Risks / Trade-offs

- **[Risk] Exit code clobbering**: A cleanup function could inadvertently overwrite the return code of `run_update.py` / `run_index.py`.
  → *Mitigation*: Capture `EXIT_CODE=$$?` as the very first operation inside the cleanup trap handler, and explicitly `exit $$EXIT_CODE`.
- **[Risk] Docker unavailable on host**: Environments without Docker or Docker daemon inactive could produce stderr noise in trap handlers.
  → *Mitigation*: Protect all cleanup commands with `command -v docker` and `docker info` checks matching existing Makefile conventions.
