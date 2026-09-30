## Context

The existing mykg sandbox harness (`docker-compose.ai_sandbox.yml`, `agy_daemon.py`, `allowlist.conf`) provides a proven pattern for running an autonomous AI CLI inside a Docker container with surgical egress filtering, credential isolation, and a filesystem inbox/outbox protocol. The opencode CLI (`opencode run --auto`) offers an equivalent non-interactive execution mode with model selection via `-m provider/model`. The auth model differs: opencode stores its API key in `~/.local/share/opencode/auth.json` (a JSON file with an `sk-` key) rather than agy's OAuth token file. The network endpoints also differ: opencode connects to `api.opencode.ai` rather than Google's generative language APIs.

See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Reuse the existing sandbox proxy infrastructure (dual-network, sidecar pattern) for the opencode daemon
- Provide a drop-in `AI_AGENT=opencode` selector in the Makefile that mirrors the existing agy workflow
- Maintain identical security posture: read-only rootfs, dropped caps, non-root user, egress allowlisting, credential isolation
- Support all opencode Go models (e.g., `opencode-go/qwen3.7-plus`, `opencode-go/deepseek-v4-pro`) via the `MODEL` Makefile variable
- Keep the agy path as the default; no breaking changes to existing workflows

**Non-Goals:**
- Running both agy and opencode daemons simultaneously (single active agent per run)
- Supporting opencode's interactive TUI mode inside the container (only `opencode run --auto` is used)
- Modifying the mykg inbox/outbox filesystem protocol (it is agent-agnostic by design)
- Adding opencode provider support to the `mykg_config.yaml` direct-API profiles (only the `agent` provider path is needed)
- Building a custom opencode Docker image (we mount the host binary, same as agy)

## Decisions

### Decision 1: Mount host opencode binary rather than baking into image
**Choice:** Bind-mount `$(which opencode)` into the container at `/usr/local/bin/opencode:ro`, identical to how `agy` is mounted.
**Rationale:** Avoids maintaining a separate Dockerfile for opencode. The host binary is already installed and version-managed by `opencode upgrade`. Keeps the container image as `python:3.11-slim` (same as agy daemon) — the daemon script is Python, and opencode is a self-contained ELF binary.
**Alternative considered:** Building a dedicated `opencode-slim` image with the binary baked in. Rejected because it adds image-build complexity and version-sync burden for no security benefit.

### Decision 2: Separate allowlist file for opencode endpoints
**Choice:** Create `deploy/sandbox_proxy/allowlist-opencode.conf` with opencode-specific endpoints. The proxy selects which allowlist to load based on the `AI_AGENT` environment variable.
**Rationale:** Surgical separation of concerns — each agent's network requirements are independently auditable. Prevents accidental permission creep where both Google and opencode endpoints are open simultaneously.
**Alternative considered:** A single unified allowlist with all endpoints. Rejected because it violates least-privilege: the agy daemon never needs opencode endpoints and vice versa.

### Decision 3: Proxy reads AI_AGENT env var to select allowlist
**Choice:** Extend `proxy.py` to accept an `AI_AGENT` environment variable (default: `agy`) that determines which `.conf` file to load at startup. The Makefile passes this variable when launching the proxy.
**Rationale:** Minimal change to the proxy — it already loads `allowlist.conf` at startup. Adding a conditional file path based on an env var is a ~5-line change. Keeps the proxy container shared between both daemons.
**Alternative considered:** Running two separate proxy instances (one per agent). Rejected as unnecessary complexity — only one daemon runs at a time.

### Decision 4: opencode_daemon.py reuses agy_daemon.py sanitization patterns
**Choice:** Copy the `REDACTED_PATTERNS`, `sanitize_task_payload()`, `clean_json_fences()`, and `SECURITY_GUARDRAIL` constants from `agy_daemon.py` into `opencode_daemon.py`. The only difference is the CLI invocation: `opencode run --auto -m <model>` instead of `agy --dangerously-skip-permissions -p <prompt>`.
**Rationale:** Defense-in-depth — the daemon-level sanitization is independent of the proxy-level egress filtering. Both layers should be present for both agents. Code duplication is acceptable here because the daemon scripts are small (~270 lines), independently deployable, and must not share runtime imports (they run in separate containers).
**Alternative considered:** Extracting shared sanitization into a common module. Rejected because it would require volume-mounting an additional shared path into both containers, increasing attack surface for a trivial amount of code.

### Decision 5: Per-agent default models and minimal effort with overrides
**Choice:** Each agent has its own default model and effort in the Makefile:
- `AGY_DEFAULT_MODEL ?= gemini-3.8-flash-low`, `AGY_DEFAULT_EFFORT ?= low`
- `OPENCODE_DEFAULT_MODEL ?= opencode-go/qwen3.7-plus`, `OPENCODE_DEFAULT_EFFORT ?= minimal`

The effective model/effort is resolved as: `MODEL`/`EFFORT` override (if specified) → agent-specific default. The daemon scripts receive the resolved values via environment variables.

**Rationale:** Operators should be able to switch agents with just `AI_AGENT=opencode` — no need to also specify `MODEL` or `EFFORT`. Both agents default to minimal effort to reduce cost and latency during indexing. The `MODEL` and `EFFORT` variables remain available as explicit overrides for either agent.

**Note:** opencode models use `provider/model` format (e.g., `opencode-go/qwen3.7-plus`). The opencode daemon maps effort to `--variant` flag: `minimal`→`minimal`, `low`→`minimal`, `medium`→default, `high`→`high`.

### Decision 6: Credential mount path
**Choice:** Mount `~/.local/share/opencode/auth.json` at `/run/secrets/opencode-auth.json:ro`. The daemon bootstraps it to `$HOME/.local/share/opencode/auth.json` at startup.
**Rationale:** Mirrors the agy pattern exactly (secret at `/run/secrets/`, bootstrapped to `$HOME/...`). Only the API key JSON file is mounted — no other opencode config, cache, or state directories are exposed.

### Decision 7: opencode permission lockdown via `OPENCODE_PERMISSION`
**Choice:** Set `OPENCODE_PERMISSION={"permission":{"bash":"deny","edit":"deny","write":"deny","read":"deny","glob":"deny","grep":"deny","webfetch":"deny","websearch":"deny","task":"deny","external_directory":"deny"}}` as an environment variable on the `mykg-opencode-daemon` container.
**Rationale:** Unlike agy (which is text-in/text-out by construction), opencode is an autonomous agent with bash, file I/O, and web tools enabled by default. The `--auto` flag auto-approves all permission prompts. Without explicit deny rules, a prompt-injected task payload could: (1) use bash to read the API key from the credential mount, (2) write corrupted data to the rw-mounted knowledge graph, (3) use webfetch to exfiltrate data through allowed endpoints. opencode's docs confirm: "Explicit deny rules are still enforced. Auto mode only changes requests that would otherwise ask for approval." This single env var neutralizes the entire tool-use attack surface, making opencode behave like agy's text-in/text-out model.
**Alternative considered:** Mounting a container-local `opencode.json` with deny rules. Rejected because env var injection is simpler and doesn't require an additional volume mount.

### Decision 8: `--pure` flag for plugin suppression
**Choice:** Add `--pure` to the `opencode run` CLI invocation in `opencode_daemon.py`.
**Rationale:** opencode supports plugins and MCP servers that can add new tools, make network requests to arbitrary endpoints, and read/write files outside the workspace. The `--pure` flag disables all external plugins, reducing the tool surface to opencode's built-in tools only (which are further restricted by Decision 7's permission lockdown).

### Decision 9: Tmpfs size limits to prevent OOM
**Choice:** Set explicit size limits on tmpfs mounts: `/tmp:size=32M` and `/home/appuser:size=64M`.
**Rationale:** opencode creates substantial state on disk (SQLite DB can exceed 500MB on the host). Without size limits, tmpfs consumes unbounded RAM (backed by host memory), potentially triggering OOM kills. The 64M limit for `$HOME` is sufficient for the auth.json bootstrap and minimal opencode state. If opencode requires more state storage, the container memory limit can be increased from 512M to 768M.

## Risks / Trade-offs

- **[Risk] opencode CLI may require additional network endpoints not yet discovered** → Mitigation: Start with `api.opencode.ai` and `opencode.ai` in the allowlist. Run initial tests with proxy logging enabled to capture any blocked connections. Add endpoints incrementally based on observed traffic.
- **[Risk] opencode `--auto` flag may have different security semantics than agy `--dangerously-skip-permissions`** → Mitigation: The `--auto` flag auto-approves permissions not explicitly denied. The sandbox's read-only filesystem, dropped caps, and egress filtering provide the actual security boundary. The daemon's prompt sanitization and guardrail injection add defense-in-depth.
- **[Risk] opencode binary may have different libc/runtime requirements than the python:3.11-slim base image** → Mitigation: The opencode binary is a dynamically-linked ELF. If it fails inside the container, we can switch to a `debian:bookworm-slim` base or statically-linked build. Test early.
- **[Trade-off] Code duplication between agy_daemon.py and opencode_daemon.py** → Accepted. The scripts are small, independently testable, and run in isolated containers. Shared module extraction would add volume-mount complexity for minimal gain.
- **[Trade-off] Single active agent per run (no parallel agy+opencode)** → Accepted. Simplifies proxy allowlist selection, cleanup traps, and container naming. Operators who need both can run them sequentially.
