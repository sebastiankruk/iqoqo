## Context

See `proposal.md` for the motivation to transition from chat agent orchestration to an autonomous daemon. The myKG extraction process relies on `mykg_config.yaml` using the `agent-claude-code` profile, which writes tasks to an inbox (`agent_inbox/*.task.json`) and polls for sentinel files in an outbox (`agent_outbox/*.done`). 

We must drain this inbox by evaluating LLM prompts. To maintain data sovereignty, we use the Antigravity CLI (`agy -p`) with the `--dangerously-skip-permissions` flag so that we route through the exact same opencode environment and models.

## Goals / Non-Goals

**Goals:**
- Provide a silent, background daemon script that orchestrates `agent-claude-code` tasks via `agy`.
- Sandbox the daemon execution in a Docker container to protect the host workspace from hypothetical prompt injections running unauthorized tools.
- Decouple the `iqoqo-mykg` Antigravity skill from manual subagent task orchestration.

**Non-Goals:**
- Changing the underlying `mykg` library pipeline or inbox/outbox protocol.
- Migrating to `openrouter-free` or other third-party APIs.

## Decisions

### 1. The Daemon Script (`agy_daemon.py`)
- **Decision:** Write a simple Python daemon that globs `*.task.json`, formats the internal LLM prompt, and calls `subprocess.run(["agy", "-p", prompt, "--dangerously-skip-permissions"])`.
- **Rationale:** `agy -p` directly accesses the local Antigravity environment (Gemini models/API keys configured by the user). It runs without UI prompts because of `--dangerously-skip-permissions`.
- **Alternatives:** We considered using the Antigravity Python SDK directly, but shelling out to the CLI is simpler and inherits the configured environment seamlessly.

### 2. Concurrency via ThreadPoolExecutor
- **Decision:** The daemon will use `ThreadPoolExecutor(max_workers=2)` to process inbox files in parallel.
- **Rationale:** Processing sequentially would be too slow. `mykg` uses `max_workers: 2` by default. Invoking 2 concurrent `agy` processes ensures high throughput without overloading the system.

### 3. Docker Sandboxing
- **Decision:** The daemon will run inside a `python:3.11-slim` Docker container. The Antigravity binary (`/usr/local/bin/agy`) and `~/.gemini` will be mounted read-only (except caches), while only `.agents` (read-only) and `mykg_sessions` (read-write) are mounted from the workspace.
- **Rationale:** `--dangerously-skip-permissions` is dangerous if the LLM output (which includes extracted markdown from the codebase) manages to trigger an Antigravity tool (like `run_command` or `write_to_file`). By running inside Docker with no access to the host's `/workspace` (other than `mykg_sessions`), any rogue tool call will harmlessly fail or only affect the disposable session artifacts.
- **Alternatives:** Running `agy_daemon.py` directly on the host was rejected by the user due to the risk of uncontrolled execution.

## Risks / Trade-offs

- **Risk**: `agy` container startup overhead or caching issues (e.g. read-only `.gemini` blocking cache writes).
  - **Mitigation**: We mount `~/.gemini` with appropriate permissions to allow the language server and SQLite db to function, but restrict the actual workspace.
- **Risk**: The Antigravity CLI binary (`agy`) requires a specific libc version that might not match the container.
  - **Mitigation**: We tested running `agy` inside `ubuntu:22.04` and `python:3.11-slim` and confirmed it executes successfully.
