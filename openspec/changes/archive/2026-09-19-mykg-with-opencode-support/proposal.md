## Why

All mykg knowledge-graph indexing currently depends on a single AI agent backend — `agy` (Antigravity CLI) running in a sandboxed Docker container with surgically-scoped egress filtering. This creates a single-vendor lock-in: if the Antigravity/Gemini ecosystem is unavailable, rate-limited, or if a better model becomes available through opencode Go, there is no way to switch. We need a parallel harness that lets operators choose between `agy` and `opencode` as the sandboxed LLM agent for mykg indexing, with the same security guarantees (egress allowlisting, credential isolation, yolo/auto-approve mode) and the same filesystem inbox/outbox protocol.

## What Changes

- **New `opencode_daemon.py`**: A daemon script mirroring `agy_daemon.py` that watches the mykg agent inbox, dispatches tasks to `opencode run --auto -m <provider/model>`, and writes `.answer.json` + `.done` sentinels to the outbox. Includes the same prompt sanitization and security guardrails.
- **New Docker service `mykg-opencode-daemon`**: Added to `docker-compose.ai_sandbox.yml` alongside the existing `mykg-agy-daemon`. Same hardening profile (read-only rootfs, dropped caps, non-root user, resource limits). Mounts only `~/.local/share/opencode/auth.json` as the surgical credential mount.
- **Extended egress allowlist**: A new `allowlist-opencode.conf` (or conditional entries in the existing allowlist) permitting only opencode Go API endpoints (`api.opencode.ai`, `opencode.ai`, and related auth/telemetry hosts). The proxy container selects the allowlist based on which daemon is active.
- **Makefile `AI_AGENT` selector with per-agent default models and minimal effort**: A new `AI_AGENT` variable (default: `agy`) that controls which daemon is launched. Each agent has its own default model (`agy`: `gemini-3.8-flash-low`, `opencode`: `opencode-go/qwen3.7-plus`) and both agents default to minimal effort (`agy`: `low`, `opencode`: `minimal` variant). Operators can switch agents with just `AI_AGENT=opencode` — no need to specify `MODEL` or `EFFORT`. The `MODEL` and `EFFORT` variables remain available as overrides.
- **mykg config profile `agent-opencode`**: A new profile in `mykg_config.yaml` with `provider: agent` and opencode-appropriate defaults (context window, timeout, model metadata). The Makefile passes `--profile agent-opencode` when `AI_AGENT=opencode`.
- **BATS and pytest coverage**: Regression tests verifying the opencode daemon lifecycle, allowlist enforcement, credential mount isolation, and Makefile selector logic.

## Capabilities

### New Capabilities
- `mykg-opencode-agent-harness`: Sandboxed Docker harness for running opencode CLI as a mykg indexing agent — daemon script, Docker Compose service, egress allowlist, credential mount, and Makefile integration.

### Modified Capabilities
- `ai-sandbox-egress-filtering`: Egress allowlist must support opencode Go API endpoints in addition to Google/Gemini endpoints, with agent-aware selection ensuring only the active backend's endpoints are permitted.

## Impact

- **Docker**: New service in `docker-compose.ai_sandbox.yml`; new or extended allowlist config; shared proxy infrastructure reused.
- **Scripts**: New `.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py` alongside `agy_daemon.py`.
- **Makefile**: `mykg-update` and `mykg-index` targets gain `AI_AGENT` conditional logic; cleanup traps extended to tear down either daemon.
- **Config**: `mykg_config.yaml` gains a new `agent-opencode` profile.
- **Credentials**: Mounts `~/.local/share/opencode/auth.json` (read-only) instead of the Gemini OAuth token when opencode is selected.
- **Tests**: `tests/bash/mykg_tooling.bats` and `tests/test_iqoqo_mykg.py` extended for opencode paths.
- **No breaking changes**: The default `AI_AGENT=agy` preserves existing behavior. Users opt in to opencode explicitly.
