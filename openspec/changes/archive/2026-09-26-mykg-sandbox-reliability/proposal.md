## Why

The myKG agent sandbox suffers from two reliability issues during task execution. First, a race condition exists during `make mykg-update` where the daemon container is launched with `--no-deps`, bypassing the egress proxy's health check. This causes initial LLM requests to fail with `connection refused` until the proxy is healthy. Second, the myKG orchestrator (`agent_adapter.py`) lacks a fail-fast mechanism when daemons encounter a hard failure (e.g., daemon crash or immediate auth error); it blindly waits the full timeout duration (up to 30 minutes) for a `.done` sentinel that will never arrive, blocking the entire pipeline.

## What Changes

- **Proxy Health Synchronization**: Remove the `--no-deps` flag in the `Makefile` so Docker Compose correctly blocks the daemon's startup until the `sandbox-egress-proxy` reports healthy.
- **Fail-Fast Error Sentinel Protocol**: Introduce an `.error` sentinel convention to the filesystem inbox/outbox protocol. The daemons will write `<task_id>.error` instead of `<task_id>.done` when a hard failure occurs.
- **Orchestrator Adapter Patch**: Monkeypatch or extend `mykg.llm.agent_adapter.AgentAdapter` within the host-side `run_update.py` script to monitor for the `.error` sentinel in addition to `.done`, immediately raising an exception and failing fast when detected instead of waiting for the full timeout.

## Capabilities

### New Capabilities
- `operations/mykg-sandbox-reliability`: Orchestration and execution reliability guarantees for the myKG agent sandbox, including startup synchronization and fail-fast sentinel protocols.

### Modified Capabilities
- `mykg-opencode-agent-harness`: Update to explicitly require writing an `.error` sentinel on terminal failures (this capability delta will enforce the new protocol on the daemon side).

## Impact

- **Affected code**: `Makefile`, `.agents/skills/iqoqo-mykg/scripts/run_update.py`, `.agents/skills/iqoqo-mykg/scripts/daemon_core.py` (which we just extracted in C30), and `.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py`.
- **System Impact**: Prevents 30-minute hangs on immediate errors, eliminates spurious proxy connection logs at startup.
