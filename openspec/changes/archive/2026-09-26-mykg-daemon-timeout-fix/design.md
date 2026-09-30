## Context

See proposal.md for motivation. Currently `agy_daemon.py` (273 lines) and `opencode_daemon.py` (364 lines) share ~70% identical logic: redaction patterns, security guardrail text, JSON fence stripping, task discovery, answer envelope writing, signal handling, and worker pool dispatch. The only meaningful differences are:

1. **CLI invocation**: `agy --dangerously-skip-permissions -p <prompt> --model X --effort Y` vs `opencode run --auto --pure -m <model> [--variant V] <prompt>`
2. **Output capture**: agy uses `capture_output=True`; opencode uses temp-file redirect to avoid pipe deadlock.
3. **Credential bootstrap**: agy copies an OAuth token; opencode copies an auth.json.
4. **Effort mapping**: opencode needs a `map_effort_to_variant()` function; agy passes effort directly.

Everything else is duplicated.

## Goals / Non-Goals

**Goals:**

- Extract all shared logic into `.agents/skills/iqoqo-mykg/scripts/daemon_core.py`
- Both daemons import from `daemon_core` and only implement their CLI-specific `invoke_cli()` function
- `compute_effective_timeout()` honors `timeout_seconds` from task JSON, preventing premature subprocess kills
- Existing tests in `tests/test_iqoqo_mykg.py` continue to pass (backward-compatible module API)
- New tests cover timeout negotiation, sanitization, and answer-writing in the shared core

**Non-Goals:**

- Changing Makefile `--workers` count (operational tuning, not a code fix)
- Fixing the proxy startup race condition (`--no-deps` vs `depends_on`) — separate concern
- Changing the myKG orchestrator's own timeout logic
- Modifying Docker Compose service definitions

## Decisions

### Decision 1: Composition over inheritance for CLI adapters

**Choice**: Each daemon defines a `CLIAdapter` protocol (or simple callable) that `daemon_core.run_daemon()` accepts as a parameter. The adapter is a function `(task_data, outbox_dir, timeout, model, effort) -> bool`.

**Why not inheritance**: The daemons are scripts, not classes. A functional approach (pass a callable) keeps them lightweight and testable without an OOP hierarchy. Each daemon's `main()` constructs its adapter and passes it to `daemon_core.run_daemon()`.

**Alternatives considered**:
- ABC base class: Adds unnecessary OOP ceremony for scripts that are <100 lines once deduplicated.
- Template method pattern: Same issue — over-engineering for two simple adapters.

### Decision 2: Timeout formula — `max(task_timeout, base + prompt_bonus)`

**Choice**: `compute_effective_timeout(task_timeout_seconds, prompt_length, default_timeout=300, base_timeout=600)` returns `max(task_timeout_seconds or default_timeout, base_timeout + prompt_length // 1000)`.

**Why this formula**: The task's `timeout_seconds` is the orchestrator's patience ceiling — the daemon must never kill a process before the orchestrator would. The `base + prompt_bonus` provides a dynamic floor for tasks that don't specify a timeout. Using `max()` means the larger of the two wins.

**Alternatives considered**:
- Always use `timeout_seconds` from task: Would break for tasks without it (missing field defaults to `None`).
- Always use prompt-based formula: Would ignore the orchestrator's explicit patience, risking the original timeout bug.

### Decision 3: Shared module location

**Choice**: `.agents/skills/iqoqo-mykg/scripts/daemon_core.py` — same directory as both daemons.

**Why**: Both daemons already live here and are loaded via `importlib` in tests. No package restructuring needed. The Docker container mounts `.agents:ro` so the new file is automatically available.

### Decision 4: Test location

**Choice**: Add tests to existing `tests/test_iqoqo_mykg.py` using the same `_load_module` pattern.

**Why**: Tests for all mykg scripts are already consolidated there. Adding a new fixture `daemon_core_module` follows the established pattern (`agy_daemon_module`, `run_update_module`). Avoids fragmenting test discovery across multiple files.

## Risks / Trade-offs

- **[Risk] Backward-incompatible module API change** → Mitigation: Both daemons' public functions (`process_task`, `run_daemon`, `main`) keep the same signatures. Internal helpers move to `daemon_core` but existing test fixtures still work because the daemons re-export or delegate.
- **[Risk] Docker container doesn't see new `daemon_core.py`** → Mitigation: The `.agents` directory is already mounted read-only into both containers. No Dockerfile or volume change needed.
- **[Risk] Import path issues inside Docker container** → Mitigation: Both daemons already use direct file imports via `sys.path` manipulation or relative imports. `daemon_core.py` in the same directory is importable via `from daemon_core import ...` after `sys.path.insert(0, script_dir)`, matching the existing pattern.
