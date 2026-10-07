## Context

See `proposal.md` — Why. The relevant current-state facts that shape the approach:

- myKG is reachable only through a closed set of entry points: seven Makefile targets, three command/workflow files (`/mykg`, `/iqoqo-mykg`), one MCP registration, and the `iqoqo-mykg` skill. No Flask route, frontend route, Celery task, database table, or migration references it. The only application-adjacent artifact is `deploy/sandbox_proxy/`, which exists solely as the myKG daemons' egress filter.
- The sandbox is a self-contained Compose project (`docker-compose.ai_sandbox.yml`) with two daemons and one proxy. Its only consumers are `scripts/mykg_sync.sh` and `scripts/probe_opencode_harness.sh`.
- Six published OpenSpec capabilities describe myKG and the sandbox: `ai-sandbox-egress-filtering`, `mykg-daemon-shared-core`, `mykg-opencode-agent-harness`, `mykg-agent-queue-management`, `operations/mykg-sandbox-reliability`, and one requirement inside `semantic-memory-harness`.
- The AI personas (9 Gems + 9 Skills) each carry a stale `## Current State` / `## Upcoming (v0.8.0 & Beyond)` block that mentions myKG and predates v0.8.1/0.8.2. The `ai-tools-harmonizer` skill owns rewriting those blocks.
- Runtime state (`.iqoqo-mykg/`, `mykg_sessions` symlink, `.env.mykg`) is untracked and gitignored; `mykg_sessions` points at a Dropbox directory that is **not** part of the repository.

## Goals / Non-Goals

**Goals:**

- Remove every tracked myKG and AI-sandbox artifact, and every reference to them, so a fresh clone contains no myKG code, config, docs, tests, specs, or AI directives.
- Keep the remaining knowledge tooling (`CodeGraph`, `Graphify`, `MemPalace`) fully intact and coherent as a trio.
- Leave `make lint` and `make test` green after the removal.
- Record the decommission as an OpenSpec change with deltas that retire the six capabilities.
- Bring the AI personas up to date for v0.8.3.

**Non-Goals:**

- Do not touch application runtime code, API, database schema, migrations, or the frontend.
- Do not remove `scripts/sync_agy_memory.sh` or the agy session-memory pipeline — that is the antigravity transcript sync and is independent of myKG. Only its myKG-specific filter lines are dropped.
- Do not delete the Dropbox `mykg_sessions` data itself; only the repository symlink to it.
- Do not uninstall the `mykg` package from `.venv/` as a hard requirement of the change (the venv is untracked); document it as an optional cleanup.

## Decisions

### Delete rather than archive the myKG code

Archived OpenSpec change history already preserves *why* the sandbox was built and hardened; the code itself has no future use, and a "dormant" copy would keep every ignore-file, lint, and test exemption alive for a tool nobody runs. Decision: hard-delete the tracked files and let `openspec/changes/archive/` remain the historical record.

- Alternative considered: move the skill to a `legacy/` directory. Rejected — it would still need Makefile wiring, ignore entries, and test exclusions, and would drift.

### Retire the six capabilities via `REMOVED Requirements` deltas

OpenSpec's delta model expresses removal as `## REMOVED Requirements` with a Reason and Migration, applied to the published spec at archive time. This keeps the *published* specs a true description of the system after the change, instead of leaving capabilities that describe deleted code.

- Alternative considered: set `skip_specs: true` because this is "tooling". Rejected — the published specs *are* the behavior contract being withdrawn, and leaving them would misdescribe the system.

### `make knowledge-sync-full` becomes MemPalace-only

The target currently runs `mempalace-index` and `mykg-update` in parallel. With myKG gone it runs `mempalace-index` alone. `memory-presync` loses its `.iqoqo-mykg-scope.yaml` sed patch but keeps the agy transcript sync.

- Alternative considered: delete `knowledge-sync-full` entirely. Rejected — the MemPalace full hallway index is still a legitimate scheduled operation and is referenced by the `semantic-memory-harness` spec.

### The knowledge-tools directive becomes a trio

`.agents/rules/iqoqo-standards.md`, `.agents/workflows/project-rules.md`, and the `code-reviewer` skill/workflow each list four memory tools. myKG's question ("how do FRBR entities relate in formal RDF?") is dropped; CodeGraph, Graphify, and MemPalace cover the remaining navigation, architecture, and decision-memory questions. `.agents/mcp_config.json`, which registered only the myKG MCP server, is deleted.

### Untracked state is removed from the working tree but not from Dropbox

`.iqoqo-mykg/` and the `mykg_sessions` symlink are deleted; `.env.mykg` is deleted. The Dropbox target is left alone because it may hold unrelated user data and is outside the repository.

## Risks / Trade-offs

- [Losing the formal RDF/Turtle ontology that `mykg-ask` served] → The application already exposes RDF/JSON-LD and SPARQL, and the ontology lives in `docs/ontology/` and `openspec/specs/`. The `ontologist-expert` skill is updated to consult those instead of `mykg_sessions/*/output/knowledge_graph.ttl`.
- [Deleting `deploy/sandbox_proxy/` could break an unrelated import] → Verified: the only importer is `tests/test_sandbox_proxy.py`, which is removed in the same change; nothing under `app/` imports it.
- [Stale AI personas keep telling agents to run `make mykg-ask`] → The `ai-tools-harmonizer` pass rewrites the Current State / Upcoming blocks and the explicit myKG references in the same change; a post-change grep for `mykg` is the verification.
- [The `.venv` still has `mykg` installed] → Harmless and untracked; documented as optional cleanup in `docs/MEMORY.md`. No tracked command invokes it after the change.
- [OpenSpec `validate` fails on fully-removed capabilities] → Validate after writing; if the tool rejects an all-removed delta, fall back to marking the spec file for deletion in tasks and deleting the published spec directory directly.

## Migration Plan

1. Delete the tracked myKG/sandbox files and tests.
2. Rewrite the referencing files (Makefile, scripts, ignore files, AI directives, docs).
3. Update the OpenSpec deltas and (optionally) `openspec validate` the change.
4. Refresh the AI personas with the harmonizer.
5. Remove the untracked runtime artifacts from the working tree.
6. Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`; then a repo-wide `grep -ri mykg` must return nothing tracked.

**Rollback**: revert the single commit; the change is file deletions plus edits with no runtime or schema side effects. Archived OpenSpec changes are untouched and remain the recovery source for the removed scripts.
