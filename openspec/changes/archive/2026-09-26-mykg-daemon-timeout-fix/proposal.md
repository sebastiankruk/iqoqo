## Why

Both myKG agent daemon harnesses (`agy_daemon.py` and `opencode_daemon.py`) ignore the `timeout_seconds` field from task payloads and instead hardcode their own subprocess timeout (300s for agy, ~672s for opencode). When the myKG orchestrator emits a large task (e.g. `normalize_names` with 16,275 entity names across 35 types, `timeout_seconds: 1800`), the daemon kills the subprocess prematurely, never writes the `.done` sentinel, and the single worker blocks all subsequent tasks until the orchestrator's own 1,800s patience expires. The two daemons also share no code despite having nearly identical task-dispatch, sanitization, and lifecycle logic — meaning every bug must be diagnosed and fixed in two places.

## What Changes

- **Extract shared daemon core module**: Factor out duplicated logic (task discovery, payload sanitization, security guardrail injection, JSON fence stripping, timeout negotiation, answer envelope writing, signal handling, worker pool dispatch) into a new `daemon_core.py` module that both `agy_daemon.py` and `opencode_daemon.py` import.
- **Honor task-level `timeout_seconds`**: Both daemons will read `task_data.get("timeout_seconds")` and use it as a floor when computing the effective subprocess timeout, so the daemon never kills a subprocess before the orchestrator's own patience expires.
- **Dynamic timeout formula**: Unify the timeout formula across both daemons: `effective_timeout = max(task_timeout, base_timeout + prompt_size_bonus)`, where `base_timeout` is 600s and `prompt_size_bonus` is `len(prompt) // 1000`.
- **Add tests for shared core**: Introduce a test suite covering timeout negotiation, payload sanitization, task discovery, and answer-envelope writing so future regressions are caught in CI.

## Capabilities

### New Capabilities

- `mykg-daemon-shared-core`: Shared daemon core module (`daemon_core.py`) providing unified task dispatch, timeout negotiation, sanitization, and lifecycle management for all myKG agent harnesses.

### Modified Capabilities

- `mykg-opencode-agent-harness`: The opencode daemon's task processing requirement changes to mandate honoring `timeout_seconds` from task payloads and importing shared logic from `daemon_core.py` instead of duplicating it.

## Impact

- **Files modified**: `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py`, `.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py`
- **Files created**: `.agents/skills/iqoqo-mykg/scripts/daemon_core.py`
- **Tests created**: `tests/scripts/test_daemon_core.py`
- **No API changes**: This is an internal tooling fix; no user-facing APIs or database schemas are affected.
- **No Makefile changes needed**: The `--workers 1` setting and proxy startup race are separate operational concerns outside this spec's scope.
