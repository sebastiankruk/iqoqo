## 1. OpenCode Daemon Script

- [x] 1.1 Create `.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py` mirroring `agy_daemon.py` structure: argparse CLI, `process_task()`, `run_daemon()`, signal handling, ThreadPoolExecutor. Replace the `agy --dangerously-skip-permissions -p <prompt>` invocation with `opencode run --auto -m <model> --variant <variant>`. Verify the script is syntactically valid with `python3 -c "import ast; ast.parse(open('.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py').read())"`
- [x] 1.2 Copy `REDACTED_PATTERNS`, `sanitize_task_payload()`, `clean_json_fences()`, and `SECURITY_GUARDRAIL` from `agy_daemon.py` into `opencode_daemon.py`. Verify sanitization works by running a unit test that feeds a prompt containing `https://www.googleapis.com/...` and base64 blobs, asserting they are redacted
- [x] 1.3 Implement credential bootstrap in `opencode_daemon.py`: at startup, copy `/run/secrets/opencode-auth.json` to `$HOME/.local/share/opencode/auth.json` with `0600` permissions. Log a warning if the secret mount is missing. Verify by checking the file-copy logic in isolation
- [x] 1.4 Implement model/effort translation: read `OPENCODE_MODEL` env var (fallback to `MYKG_MODEL`), map effort levels (`low`→`minimal`, `medium`→default, `high`→`high`) to opencode's `--variant` flag. Verify the mapping logic with a unit test

## 2. Egress Allowlist for OpenCode

- [x] 2.1 Create `deploy/sandbox_proxy/allowlist-opencode.conf` with opencode Go API endpoints: `api.opencode.ai:443`, `opencode.ai:443`. Include header comments matching the style of `allowlist.conf`. Verify the file exists and contains only port-443 entries
- [x] 2.2 Extend `deploy/sandbox_proxy/proxy.py` to read an `AI_AGENT` environment variable (default: `agy`) and load the corresponding allowlist file (`allowlist.conf` for agy, `allowlist-opencode.conf` for opencode). Fail closed if the variable is unrecognized or the file is missing. Verify by running the proxy with `AI_AGENT=opencode` and confirming it loads the correct allowlist in log output

## 3. Docker Compose Service

- [x] 3.1 Add `mykg-opencode-daemon` service to `docker-compose.ai_sandbox.yml` with identical hardening to `mykg-agy-daemon`: `user: "1000:1000"`, `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]`, `read_only: true`, resource limits (0.50 CPU, 512M memory), tmpfs for `/tmp` and `/home/appuser`. Verify with `docker compose -f docker-compose.ai_sandbox.yml config` that the service is valid
- [x] 3.2 Configure volume mounts for `mykg-opencode-daemon`: `./mykg_sessions:/workspace/mykg_sessions:rw`, `./.agents:/workspace/.agents:ro`, `~/.local/share/opencode/auth.json:/run/secrets/opencode-auth.json:ro`. Verify no other host paths are mounted
- [x] 3.3 Set environment variables for the opencode daemon service: `HOME=/home/appuser`, proxy env vars (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`), `AI_AGENT=opencode`. Ensure it depends on `sandbox-egress-proxy` health check and is on `sandbox-internal` network only. Verify with `docker compose config`

## 4. Makefile AI Agent Selector

- [x] 4.1 Add `AI_AGENT ?= agy` variable to the Makefile (near `MYKG_DEFAULT_MODEL`). Add per-agent default model and effort variables: `AGY_DEFAULT_MODEL ?= gemini-3.8-flash-low`, `AGY_DEFAULT_EFFORT ?= low`, `OPENCODE_DEFAULT_MODEL ?= opencode-go/qwen3.7-plus`, `OPENCODE_DEFAULT_EFFORT ?= minimal`. Add validation: if `AI_AGENT` is not `agy` or `opencode`, print an error and exit. Resolve effective model/effort as `$(if $(MODEL),$(MODEL),$(if $(filter agy,$(AI_AGENT)),$(AGY_DEFAULT_MODEL),$(OPENCODE_DEFAULT_MODEL)))` and similarly for effort. Verify with `make mykg-update AI_AGENT=invalid` producing an error message, and `make mykg-update AI_AGENT=opencode` using the opencode defaults
- [x] 4.2 Refactor `mykg-update` target: wrap daemon launch in a conditional on `$(AI_AGENT)`. For `agy`: existing logic (mount `$$AGY_BIN`, pass `MYKG_MODEL` and `MYKG_EFFORT` using resolved effective values). For `opencode`: mount `$$OPENCODE_BIN` (`which opencode`), pass `OPENCODE_MODEL` and `OPENCODE_EFFORT` using resolved effective values, launch `opencode_daemon.py` instead of `agy_daemon.py`. Cleanup trap must tear down the correct container name (`mykg-agy-daemon` or `mykg-opencode-daemon`). Verify `make mykg-update` (default) still launches agy daemon with `gemini-3.8-flash-low` and effort `low`
- [x] 4.3 Refactor `mykg-index` target with the same `AI_AGENT` conditional logic and per-agent default model/effort resolution. Verify `make mykg-index AI_AGENT=opencode` launches the opencode daemon with `opencode-go/qwen3.7-plus` and effort `minimal` (no MODEL or EFFORT override needed)
- [x] 4.4 Pass `--profile agent-opencode` to `run_update.py` / `run_index.py` when `AI_AGENT=opencode`. This requires extending the Python scripts to accept a `--profile` argument or reading it from an env var. Verify the profile flag is passed correctly

## 5. mykg Configuration Profile

- [x] 5.1 Add `agent-opencode` profile to `mykg_config.yaml` with `provider: agent`, context window 200000, model `opencode-go/qwen3.7-plus` (informational), timeout 1800, inbox/outbox dirs `agent_inbox`/`agent_outbox`, and the same pipeline settings as `agent-claude-code`. Update the header comment to list `agent-opencode` as an available profile. Verify with `mykg extract-graph --help` showing the profile is recognized

## 6. Tests

- [x] 6.1 Add BATS tests to `tests/bash/mykg_tooling.bats` verifying: (a) `allowlist-opencode.conf` exists and contains expected endpoints, (b) `proxy.py` loads the correct allowlist based on `AI_AGENT` env var, (c) `AI_AGENT=invalid` causes proxy to fail closed. Verify with `bats tests/bash/mykg_tooling.bats`
- [x] 6.2 Add pytest tests to `tests/test_iqoqo_mykg.py` verifying: (a) `opencode_daemon.py` sanitization redacts Google/exfiltration URLs, (b) credential bootstrap copies auth.json to correct path with correct permissions, (c) model/effort translation maps correctly. Verify with `pytest tests/test_iqoqo_mykg.py`
- [x] 6.3 Add BATS test verifying Makefile `AI_AGENT` validation: `make mykg-update AI_AGENT=invalid` exits non-zero with an error message. Verify with `bats tests/bash/mykg_tooling.bats`

## 7. Security Hardening (Post-Implementation Review)

- [x] 7.1 Add `OPENCODE_PERMISSION` environment variable to `mykg-opencode-daemon` service in `docker-compose.ai_sandbox.yml` with explicit deny rules for all tools (`bash`, `edit`, `write`, `read`, `glob`, `grep`, `webfetch`, `websearch`, `task`, `external_directory`). Verify with `docker compose config` that the env var is set
- [x] 7.2 Add `--pure` flag to the `opencode run` CLI invocation in `opencode_daemon.py` to disable external plugins and MCP servers. Verify the flag is present in the command construction
- [x] 7.3 Add explicit tmpfs size limits (`/tmp:size=32M`, `/home/appuser:size=64M`) to prevent OOM from opencode's SQLite state. Verify with `docker compose config`

## 8. Integration Verification

- [x] 8.1 Run `docker compose -f docker-compose.ai_sandbox.yml config` to validate the full compose file with both daemon services and security hardening. Verify no YAML errors
- [ ] 8.2 Run `make mykg-update AI_AGENT=opencode` end-to-end on a small test scope (no MODEL or EFFORT override — verify the defaults `opencode-go/qwen3.7-plus` and `minimal` are used). Verify the opencode daemon starts, processes at least one task from the inbox, and writes `.answer.json` + `.done` to the outbox
- [ ] 8.3 Verify egress isolation: with `AI_AGENT=opencode`, attempt a connection from inside the opencode daemon container to a Google endpoint (e.g., `generativelanguage.googleapis.com`). Verify it is blocked by the proxy. Then verify `api.opencode.ai` is permitted
