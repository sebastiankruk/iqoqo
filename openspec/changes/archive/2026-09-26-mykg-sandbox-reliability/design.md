## Context

See proposal.md for motivation. The myKG sandbox runs daemon containers via a Makefile target (`mykg-update`) that currently forces `--no-deps`. When tasks fail, the daemons (refactored into `daemon_core.py` in C30) simply exit without writing a sentinel. Meanwhile, `mykg.llm.agent_adapter.AgentAdapter.process_task` loops via `time.sleep` checking solely for the `.done` sentinel, waiting up to the full `effective_timeout` (e.g. 1800s) if the daemon has died.

## Goals / Non-Goals

**Goals:**
- Eliminate the connection-refused startup race by removing `--no-deps` from the `Makefile` and letting Compose's `depends_on: service_healthy` properly block daemon start until the proxy is ready.
- Enable `daemon_core.py` (which powers both agy and opencode daemons) to write a `.error` sentinel file upon subprocess failure or unhandled exception.
- Enable the orchestrator (via runtime monkeypatching in `run_update.py` or editing the agent adapter locally) to check for `.error` and fail fast.

**Non-Goals:**
- Re-architecting the core `mykg` LLM adapter design.
- Altering the myKG data pipeline steps.

## Decisions

### Decision 1: Proxy dependency synchronization in Makefile

**Choice**: Remove `--no-deps` from the `docker compose run` command in the `mykg-update` Makefile target.

**Why**: `docker-compose.ai_sandbox.yml` already correctly specifies `depends_on: { sandbox-egress-proxy: { condition: service_healthy } }` for both daemons. `--no-deps` was likely added to prevent accidentally spinning up the proxy if it wasn't running, but the target already starts the proxy explicitly (`docker compose up -d sandbox-egress-proxy`). Dropping `--no-deps` allows the orchestrator to wait for proxy health automatically.

### Decision 2: The `.error` sentinel protocol

**Choice**: Daemons will write `<task_id>.error` (containing a JSON object with error details) instead of `<task_id>.done` when a task fails fatally.

**Why**: This mirrors the success path (`.answer.json` and `.done`). Writing a distinct sentinel file makes it easy for the polling loop (which uses `Path.exists()`) to detect failure without having to parse every JSON envelope that appears.

### Decision 3: Patching mykg's AgentAdapter

**Choice**: Since `mykg` is a third-party dependency installed in `.venv/lib/python3.14/site-packages`, we cannot cleanly rewrite its source in this repository directly. Instead, we will monkeypatch the `_wait_for_sentinel()` method of `mykg.llm.agent_adapter.AgentAdapter` at runtime in `.agents/skills/iqoqo-mykg/scripts/run_update.py` (our host script that invokes the pipeline).

**Alternatives considered**:
- **Forking mykg**: Overkill for a 3-line fail-fast change.
- **Modifying the venv files**: Will be overwritten on next `pip install`.
- **Runtime monkeypatching**: Clean, scoped to our execution context, and easy to document. The patch will replace the polling loop with one that checks `if error_path.exists(): raise RuntimeError("Task failed")`.

## Risks / Trade-offs

- **[Risk] Monkeypatch fragility**: If `mykg` releases a new version that renames `AgentAdapter` or its polling loop method, the patch will fail.
  - **Mitigation**: Add a try/except block around the monkeypatch that logs a warning if the method signature has changed, falling back to the default (slow) timeout logic.
