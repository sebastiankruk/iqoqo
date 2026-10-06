## Purpose

Provides a sandboxed Docker harness for running the opencode CLI as an alternative LLM agent backend for mykg knowledge-graph indexing, mirroring the existing agy-based harness with equivalent security guarantees, filesystem inbox/outbox protocol, and operator-selectable model choice.

## ADDED Requirements

### Requirement: OpenCode Daemon Task Processing
The `opencode_daemon.py` SHALL watch the mykg agent inbox directory for `.task.json` files, dispatch each task to the opencode CLI via `opencode run --auto -m <provider/model>`, and write `.answer.json` plus `.done` sentinel files to the agent outbox directory upon successful completion.

#### Scenario: Task dispatched and answered via opencode CLI
- **WHEN** a `.task.json` file appears in the agent inbox directory
- **THEN** the daemon SHALL invoke `opencode run --auto` with the task prompt and the configured model
- **AND** write a `.answer.json` envelope containing the task ID and LLM response text to the outbox
- **AND** create a `.done` sentinel file in the outbox to signal completion to the mykg pipeline

#### Scenario: Concurrent task processing with configurable workers
- **WHEN** multiple `.task.json` files are present in the inbox simultaneously
- **THEN** the daemon SHALL process up to the configured number of concurrent workers (default: 2)
- **AND** each task SHALL be dispatched to a separate `opencode run` subprocess

### Requirement: OpenCode Daemon Prompt Sanitization
The opencode daemon SHALL sanitize incoming task payloads before constructing the CLI invocation, redacting exfiltration URLs, domains, and binary blobs using the same pattern set as the agy daemon.

#### Scenario: Incoming task containing exfiltration URLs is sanitized
- **WHEN** a task prompt contains URLs pointing to `googleapis.com`, Google Drive, Google Docs, cloud storage endpoints, or unbroken base64 data URIs
- **THEN** the daemon SHALL redact those patterns before passing the prompt to the opencode CLI

#### Scenario: Security guardrail prepended to every prompt
- **WHEN** the daemon constructs the prompt invocation for `opencode run`
- **THEN** the prompt SHALL include the same explicit security guardrail instructions prohibiting data exfiltration and external network requests

### Requirement: OpenCode Daemon Credential Bootstrap
The opencode daemon SHALL bootstrap the opencode Go API key from a surgically-mounted secret file into the expected location within the container's ephemeral home directory at startup.

#### Scenario: Auth file mounted from secret and bootstrapped
- **WHEN** the container starts with `~/.local/share/opencode/auth.json` mounted at `/run/secrets/opencode-auth.json`
- **THEN** the daemon SHALL copy the auth file to `$HOME/.local/share/opencode/auth.json` with `0600` permissions
- **AND** the opencode CLI SHALL be able to authenticate to the opencode Go API using this key

#### Scenario: Missing auth file produces clear error
- **WHEN** the secret mount `/run/secrets/opencode-auth.json` does not exist
- **THEN** the daemon SHALL log a warning to stderr and proceed (opencode CLI will fail with its own auth error if no key is available)

### Requirement: OpenCode Daemon Lifecycle and Clean Shutdown
The opencode daemon container SHALL support graceful shutdown on SIGINT and SIGTERM, and the Makefile orchestration SHALL perform pre-flight container removal to prevent name collisions.

#### Scenario: Daemon handles SIGINT without container leakage
- **WHEN** a running mykg indexing process with `AI_AGENT=opencode` receives SIGINT (Ctrl+C) or SIGTERM
- **THEN** the signal trap SHALL invoke teardown commands (`docker compose down` and removal of `mykg-opencode-daemon`)
- **AND** the Docker container SHALL NOT remain in running or stopped collision states

#### Scenario: Pre-flight container collision prevention
- **WHEN** an mykg indexing or update operation begins with `AI_AGENT=opencode`
- **THEN** any preexisting `mykg-opencode-daemon` container SHALL be forcibly removed prior to spawning the new container

### Requirement: Makefile AI Agent Selector with Per-Agent Default Models and Minimal Effort
The Makefile SHALL provide an `AI_AGENT` variable (default: `agy`) that controls which sandboxed daemon is launched for mykg indexing and update operations. Each agent SHALL have its own default model and both agents SHALL default to minimal effort so operators can switch agents without specifying model or effort.

#### Scenario: Default agy agent launches with minimal effort
- **WHEN** `make mykg-update` is invoked without specifying `AI_AGENT`, `MODEL`, or `EFFORT`
- **THEN** the existing `mykg-agy-daemon` container SHALL be launched with the agy binary mounted
- **AND** the model SHALL default to `gemini-3.8-flash-low`
- **AND** the effort SHALL default to `low` (agy's minimal effort level)
- **AND** behavior SHALL be identical to the current implementation

#### Scenario: OpenCode agent launches with its own defaults
- **WHEN** `make mykg-update AI_AGENT=opencode` is invoked without specifying `MODEL` or `EFFORT`
- **THEN** the `mykg-opencode-daemon` container SHALL be launched with the opencode binary
- **AND** the model SHALL default to `opencode-go/qwen3.7-plus`
- **AND** the effort SHALL default to `minimal` (opencode's minimal variant)
- **AND** the mykg pipeline SHALL use the `agent-opencode` profile

#### Scenario: MODEL and EFFORT overrides work for either agent
- **WHEN** `make mykg-update AI_AGENT=opencode MODEL=opencode-go/deepseek-v4-pro EFFORT=high` is invoked
- **THEN** the `mykg-opencode-daemon` container SHALL be launched with the specified model and effort overrides
- **AND** the `MODEL` and `EFFORT` variables SHALL take precedence over the agent's defaults

#### Scenario: Invalid AI_AGENT value rejected
- **WHEN** `make mykg-update AI_AGENT=invalid` is invoked
- **THEN** the Makefile SHALL print an error message listing valid options (`agy`, `opencode`) and exit with a non-zero status

### Requirement: OpenCode Docker Service Hardening
The `mykg-opencode-daemon` Docker Compose service SHALL apply the same hardening profile as `mykg-agy-daemon`: read-only root filesystem, dropped capabilities, non-root user, resource limits, and ephemeral tmpfs.

#### Scenario: Container runs with minimal privileges
- **WHEN** the `mykg-opencode-daemon` container starts
- **THEN** it SHALL run as user 1000:1000 with `no-new-privileges:true`, `cap_drop: [ALL]`, `read_only: true`
- **AND** CPU and memory limits SHALL be enforced via Docker deploy resources

#### Scenario: Only surgical credential and session volumes mounted
- **WHEN** the container is created
- **THEN** the following volumes SHALL be mounted: `./mykg_sessions` (rw), `./.agents` (ro), and the opencode auth.json secret (ro)
- **AND** no other host paths SHALL be accessible inside the container

### Requirement: OpenCode Tool Access Lockdown
The `mykg-opencode-daemon` container SHALL configure opencode to deny all tool access (bash, file I/O, web, etc.) via the `OPENCODE_PERMISSION` environment variable, making opencode behave as a text-in/text-out agent like agy.

#### Scenario: All tools denied by default
- **WHEN** the `mykg-opencode-daemon` container starts
- **THEN** the `OPENCODE_PERMISSION` environment variable SHALL be set with explicit deny rules for `bash`, `edit`, `write`, `read`, `glob`, `grep`, `webfetch`, `websearch`, `task`, and `external_directory`
- **AND** these deny rules SHALL NOT be overridden by the `--auto` flag

#### Scenario: Prompt injection cannot leverage tools
- **WHEN** a task payload contains instructions to use bash, read files, or make network requests
- **THEN** opencode SHALL reject all tool invocations due to the explicit deny rules
- **AND** the agent SHALL only produce text output (matching agy's threat model)

### Requirement: OpenCode Plugin Suppression
The opencode daemon SHALL invoke the opencode CLI with the `--pure` flag to disable all external plugins and MCP servers.

#### Scenario: Plugins disabled to reduce attack surface
- **WHEN** the daemon invokes `opencode run`
- **THEN** the `--pure` flag SHALL be included in the CLI invocation
- **AND** no external plugins or MCP servers SHALL be loaded

### Requirement: OpenCode mykg Configuration Profile
A new `agent-opencode` profile SHALL exist in `mykg_config.yaml` with `provider: agent` and opencode-appropriate defaults for context window, model metadata, and pipeline settings.

#### Scenario: Profile selectable via CLI flag
- **WHEN** `mykg extract-graph` is invoked with `--profile agent-opencode`
- **THEN** the pipeline SHALL use the agent provider with inbox/outbox filesystem protocol
- **AND** the profile's context window, timeout, and model metadata SHALL be applied
