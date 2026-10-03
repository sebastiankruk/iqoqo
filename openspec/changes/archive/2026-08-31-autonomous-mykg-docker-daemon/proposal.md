## Why

The current `iqoqo-mykg` knowledge engine update process relies on the Antigravity chat agent to orchestrate task extraction by spawning subagents for every chunk. Because the `agent-claude-code` profile is mandated to maintain data sovereignty (avoiding PRC servers via OpenRouter), this creates 42+ manual permission prompts in the UI unless YOLO mode is active, severely degrading developer experience and polluting the conversation log. We need a way to run these tasks completely autonomously while keeping the LLM execution isolated and secure on the trusted host.

## What Changes

- Create a new Python daemon script (`agy_daemon.py`) that watches the `mykg` agent inbox and processes tasks automatically using the Antigravity CLI (`agy -p`).
- Update the `Makefile` so that `mykg-update` spawns this daemon in the background inside a restricted Docker container (`python:3.11-slim`), ensuring the prompt execution is sandboxed with read-only access to scripts and read-write access only to `mykg_sessions`.
- Remove the manual watch loop and `invoke_subagent` logic from the `iqoqo-mykg` `SKILL.md` file, making it a fire-and-forget shell command.
- Fix a bug in `run_update.py` that fails when the scope is a list of files instead of a directory.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None. (This is a developer tooling / DX improvement; no application behavior requirements are changed. Marked with `skip_specs: true`).

## Impact

- **Developer Experience**: Eliminates 40+ manual approval prompts during knowledge graph syncs.
- **Security**: The `agy` CLI process is strictly sandboxed inside a Docker container, preventing potential prompt injections from modifying the host workspace.
- **Data Sovereignty**: Continues to use the local Antigravity (opencode) session, avoiding third-party or untrusted APIs.
