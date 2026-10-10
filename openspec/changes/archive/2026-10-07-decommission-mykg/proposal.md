## Why

myKG was an experimental RDF/Turtle knowledge-graph compiler driven by a bespoke Dockerised "AI sandbox" (agy/opencode daemons behind an egress-filtering proxy). It never became a first-class part of the product: it is an offline batch compiler costing roughly US$4.36 and 15–60 minutes per full run, it duplicates ontology knowledge the application already holds in its own RDF/JSON-LD and that MemPalace/Graphify already index for navigation, and it forces the project to carry an entire sandbox harness whose maintenance cost now exceeds its value. Release 0.8.3 is the right point to remove it cleanly — before v0.9.0 Federation work begins and while the removal is a self-contained, tooling-only change with no application-code dependency.

## What Changes

- **BREAKING** Remove all myKG tooling: the `iqoqo-mykg` skill and its scripts, the `/mykg` and `/iqoqo-mykg` workflows, the `/mykg` OpenCode command, the `mykg` MCP server registration (`.agents/mcp_config.json`), and the myKG Makefile targets (`mykg-scope`, `mykg-update`, `mykg-index`, `mykg-status`, `mykg-retry`, `mykg-probe`, `mykg-ask`).
- **BREAKING** Remove the AI sandbox harness built to run myKG: `docker-compose.ai_sandbox.yml`, `deploy/sandbox_proxy/` (egress proxy + allowlists), `scripts/mykg_sync.sh`, and `scripts/probe_opencode_harness.sh`.
- Remove myKG configuration and runtime artifacts: `mykg_config.yaml`, `.iqoqo-mykg-scope.yaml`, `.env.mykg`, the `mykg_sessions` symlink, and the `.iqoqo-mykg/` runtime state, plus the corresponding `.gitignore` / `.dockerignore` / `.graphifyignore` / `.markdownlint-cli2.jsonc` / `mempalace.yml` / `.gitleaks.toml` entries.
- Remove the myKG-specific test suites: `tests/test_iqoqo_mykg.py`, `tests/bash/mykg_tooling.bats`, and `tests/test_sandbox_proxy.py`; drop the myKG filter lines from `tests/bash/agy_memory_sync.bats`.
- Update `make knowledge-sync-full` and `make memory-presync` so they no longer invoke myKG; `knowledge-sync-full` becomes MemPalace-only.
- Remove myKG from the AI knowledge-tool directives (`.agents/rules/iqoqo-standards.md`, `.agents/workflows/project-rules.md`, `.agents/workflows/code-reviewer.md`, `.agents/skills/code-reviewer/SKILL.md`); the "Knowledge Tools Quartet" becomes a trio (CodeGraph, Graphify, MemPalace). Drop the `.mykg_sessions/` exclusions from the `iqoqo-mempalace` skill and `mempalace.yml`.
- Update `scripts/sync_version.py` and `scripts/sync_agy_memory.sh` to drop myKG references.
- Update `docs/MEMORY.md` and record the removal in `docs/CHANGELOG.md` under `[0.8.3]`.
- Refresh the AI personas (Gemini Gems and OpenCode skills) for 0.8.3 with the `ai-tools-harmonizer`: new Current State and Upcoming paragraphs, with every myKG reference removed.
- Retire the six myKG/sandbox capabilities from the published OpenSpec specs.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `semantic-memory-harness`: drop `.venv/bin/mykg` from the deterministically resolved binaries; remove the *Session-Agnostic myKG Query Target* requirement; the scheduled full sync no longer triggers a myKG update.
- `ai-sandbox-egress-filtering`: retire the capability entirely (all requirements removed).
- `mykg-daemon-shared-core`: retire the capability entirely (all requirements removed).
- `mykg-opencode-agent-harness`: retire the capability entirely (all requirements removed).
- `mykg-agent-queue-management`: retire the capability entirely (all requirements removed).
- `operations/mykg-sandbox-reliability`: retire the capability entirely (all requirements removed).

## Impact

- **Removed tooling**: `.agents/skills/iqoqo-mykg/`, `.agents/workflows/{mykg,iqoqo-mykg}.md`, `.opencode/commands/mykg.md`, `.agents/mcp_config.json`, `scripts/{mykg_sync,probe_opencode_harness}.sh`, `mykg_config.yaml`, `.iqoqo-mykg-scope.yaml`, `docker-compose.ai_sandbox.yml`, `deploy/sandbox_proxy/`.
- **Removed tests**: `tests/test_iqoqo_mykg.py`, `tests/bash/mykg_tooling.bats`, `tests/test_sandbox_proxy.py`.
- **Modified**: `Makefile`, `scripts/sync_version.py`, `scripts/sync_agy_memory.sh`, `.agents/rules/iqoqo-standards.md`, `.agents/workflows/{project-rules,code-reviewer}.md`, `.agents/skills/code-reviewer/SKILL.md`, `.agents/skills/iqoqo-mempalace/**`, `.gitignore`, `.dockerignore`, `.graphifyignore`, `.markdownlint-cli2.jsonc`, `mempalace.yml`, `.gitleaks.toml`, `docs/MEMORY.md`, `docs/CHANGELOG.md`, and the AI persona assets (9 Gems + 9 Skills).
- **Dependencies**: the untracked `mykg` package installed in `.venv/` and the `mykg_sessions` Dropbox symlink are removed from the working tree; no application runtime, API, database, or production deployment path depends on myKG.
- **No user-facing behaviour change**: no Flask route, frontend route, database schema, or migration is touched.
