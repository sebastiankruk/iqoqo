## 1. Record the change

- [x] 1.1 Write the OpenSpec artifacts (proposal, design, six delta specs, tasks) and verify `openspec status --change decommission-mykg` lists all artifacts as done
- [x] 1.2 Verify the change validates with `openspec validate decommission-mykg --strict` (or record the exact failure if all-removed deltas are rejected)

## 2. Remove the myKG tooling

- [x] 2.1 Delete `.agents/skills/iqoqo-mykg/` (SKILL.md + all scripts) and verify the directory no longer exists
- [x] 2.2 Delete `.agents/workflows/mykg.md` and `.agents/workflows/iqoqo-mykg.md` and verify both are gone
- [x] 2.3 Delete `.opencode/commands/mykg.md` and verify it is gone
- [x] 2.4 Delete `.agents/mcp_config.json` (myKG-only MCP registration) and verify it is gone
- [x] 2.5 Delete `mykg_config.yaml` and `.iqoqo-mykg-scope.yaml` and verify both are gone

## 3. Remove the AI sandbox harness

- [x] 3.1 Delete `docker-compose.ai_sandbox.yml` and verify it is gone
- [x] 3.2 Delete `deploy/sandbox_proxy/` (proxy, allowlists, `__init__.py`) and verify `grep -rn sandbox_proxy app/ scripts/` returns nothing
- [x] 3.3 Delete `scripts/mykg_sync.sh` and `scripts/probe_opencode_harness.sh` and verify both are gone

## 4. Remove the myKG tests

- [x] 4.1 Delete `tests/test_iqoqo_mykg.py` and verify `pytest --collect-only tests/test_iqoqo_mykg.py` is no longer possible (file absent)
- [x] 4.2 Delete `tests/bash/mykg_tooling.bats` and verify `bats tests/bash/` runs without it
- [x] 4.3 Delete `tests/test_sandbox_proxy.py` and verify the file is gone
- [x] 4.4 Drop the myKG filter lines from `tests/bash/agy_memory_sync.bats` and verify the remaining tests pass with `bats tests/bash/agy_memory_sync.bats`

## 5. Update orchestration

- [x] 5.1 Remove the `mykg-*` targets, `MYKG_*`/`AI_AGENT`/`AGY_*`/`OPENCODE_*` variables, `.PHONY` entries, and help text from `Makefile`; verify `make help` no longer lists myKG
- [x] 5.2 Update `knowledge-sync-full` to run `mempalace-index` only and `memory-presync` to drop the `.iqoqo-mykg-scope.yaml` sed patch; verify `make -n knowledge-sync-full` does not invoke myKG
- [x] 5.3 Remove `update_mykg_scope` and its call site from `scripts/sync_version.py`; verify `python scripts/sync_version.py --help` / a dry run no longer references `.iqoqo-mykg-scope.yaml`
- [x] 5.4 Remove the myKG-specific transcript filters from `scripts/sync_agy_memory.sh`; verify `bash -n scripts/sync_agy_memory.sh` passes

## 6. Update configuration and ignore files

- [x] 6.1 Remove the myKG entries from `.gitignore` (`.iqoqo-mykg/`, `mykg_sessions`, `.mykg_sessions`, `.mykg_work`) and verify `git check-ignore` no longer matches them
- [x] 6.2 Remove `.iqoqo-mykg` from `.dockerignore` and verify the entry is gone
- [x] 6.3 Remove `.context/notes/.mykg_sessions/` from `.graphifyignore` and verify the entry is gone
- [x] 6.4 Remove the mykg_sessions ignores from `.markdownlint-cli2.jsonc` and `mempalace.yml` and verify both files still parse (`python -c "import json"` for the JSONC; `python -c "import yaml"` for mempalace.yml)
- [x] 6.5 Remove the `mykg_sessions/` path and `.env.mykg` allowlist entries from `.gitleaks.toml` and verify `make secret-scan` passes
- [ ] 6.6 Archive the change with `openspec archive decommission-mykg` (the `.openspec.yaml` sets `retire_capabilities: true`, which OpenSpec requires to remove a capability's last requirement) so the recorded delta specs retire the five myKG/sandbox capabilities from `openspec/specs/`; verify `openspec validate --specs` passes and the retired spec directories are gone while their records remain under `openspec/changes/archive/`
- [x] 6.7 Remove the MOD-8 myKG task and references from the in-progress `v083-review-findings-sweep` change; verify `openspec validate v083-review-findings-sweep` passes

## 7. Update the AI knowledge-tool directives

- [x] 7.1 Remove the myKG directive section and the myKG entry from the "Memory Tools Integration Quartet" in `.agents/rules/iqoqo-standards.md`, renaming it a trio; verify the file (and its `.github/copilot.md` symlink) no longer mention myKG
- [x] 7.2 Remove the mykg entry from `.agents/workflows/project-rules.md` and `.agents/workflows/code-reviewer.md`; verify neither mentions myKG
- [x] 7.3 Remove the mykg MCP tool rows from `.agents/skills/code-reviewer/SKILL.md` and update the tool count to three; verify the file no longer mentions myKG
- [x] 7.4 Remove the `.mykg_sessions/` exclusions from `.agents/skills/iqoqo-mempalace/SKILL.md` and `.agents/skills/iqoqo-mempalace/scripts/scan_scope.py`; verify `python -m py_compile .agents/skills/iqoqo-mempalace/scripts/scan_scope.py` passes
- [x] 7.5 Update `.agents/skills/ontologist-expert/SKILL.md` to consult `docs/ontology/` and the application RDF/SPARQL endpoints instead of `mykg_sessions/*/output/knowledge_graph.ttl`

## 8. Update documentation

- [x] 8.1 Update `docs/MEMORY.md` to drop the myKG targets, the sandbox architecture section, and the myKG knowledge-graph references; verify it no longer mentions myKG
- [x] 8.2 Add a `### Removed` section under `[0.8.3]` in `docs/CHANGELOG.md` describing the myKG and AI-sandbox decommission

## 9. Refresh the AI personas for v0.8.3

- [x] 9.1 Rewrite the `## Current State` and `## Upcoming (v0.8.3 & Beyond)` blocks in the 9 `.gemini/gems/*.md` files with the `ai-tools-harmonizer`; verify none still says `v0.7.18`/`v0.8.0`
- [x] 9.2 Rewrite the same blocks in the 9 `.agents/skills/*/SKILL.md` persona files; verify none still says `v0.7.18`/`v0.8.0`
- [x] 9.3 Verify no persona file mentions myKG (`grep -ri mykg .gemini/gems/ .agents/skills/` returns nothing)

## 10. Clean untracked runtime state

- [x] 10.1 Remove `.env.mykg`, `.iqoqo-mykg/`, and the `mykg_sessions` symlink from the working tree (leaving the Dropbox target intact); verify none exist in the repo root

## 11. Verification

- [x] 11.1 Verify no tracked file outside the OpenSpec tree and the historical CHANGELOG mentions myKG: `git ls-files | grep -v -e '^openspec/' -e '^docs/CHANGELOG.md$' | xargs grep -il mykg` returns nothing (the myKG capabilities remain in `openspec/specs/` only until the recorded change is archived; `openspec/changes/archive/` and past CHANGELOG entries are immutable history and are intentionally preserved)
- [x] 11.2 Run `IQOQO_AI_MODE=1 make lint` and verify it passes
- [x] 11.3 Run `IQOQO_AI_MODE=1 make test` and verify the backend, frontend, and script suites pass. E2E is environment-gated: Playwright's bundled Chromium fails to launch on this host (`error while loading shared libraries: libatk-1.0.so.0`), so all 573 cases abort at `browserType.launch` for reasons unrelated to this change; this must be re-run in CI or a host with Playwright's system dependencies.
