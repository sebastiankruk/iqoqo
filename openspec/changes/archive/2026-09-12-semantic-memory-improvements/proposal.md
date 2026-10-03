# Proposal: Semantic Memory & Developer Tooling Improvements

## Why

Empirical telemetry analysis from recent sessions revealed that while semantic memory tools (`codegraph`, `mempalace`, `graphify`, `mykg`) provide high-value architectural context, structural friction points cause up to 25% of queries to fail and fall back to broad `grep_search` sweeps. Furthermore, full MemPalace indexing imposes a rigid ~15-minute (900-930s) hallway traversal penalty on CPU even when zero files change, and myKG incurs heavy multi-batch LLM costs (~9.7M tokens / ~$1.90). Coupling these heavy tools into interactive session syncs blocks developer workflows.

Improving tool execution determinism, query ergonomics, credential sanitization, and strictly separating sub-minute local sync from multi-minute batch pipelines will eliminate ~80% of grep fallbacks and ensure fast, secure, and non-blocking agent-assisted development.

## What Changes

- **Deterministic Binary Resolution**: Bind CLI tools explicitly to project virtualenv (`.venv/bin/graphify`, `.venv/bin/mykg`, `.venv/bin/mempalace`) in all skill documentation and wrappers to eliminate `command not found (exit code 127)` subshell failures.
- **MemPalace Retrieval Ergonomics & Ingestion Sanitization**:
  - Add explicit query documentation to `iqoqo-mempalace` skill with keyword optimization guidelines for MiniLM embeddings.
  - Ban suppressing stderr (`2>/dev/null`) and blind piping to `head -30` which swallows matching snippets and diagnostic errors.
  - Introduce credential and absolute path redaction pre-filter before embedding notes and transcripts into ChromaDB.
- **Session-Agnostic myKG Query Interface**:
  - Implement `make mykg-ask Q="<question>"` (and underlying runner) that auto-resolves the latest `mykg_sessions/` directory.
  - Expose compiled concept notes in `output/obsidian_vault/` for fast markdown inspection.
- **CodeGraph First-Stop Navigation Directive**:
  - Update `.agent/rules/iqoqo-standards.md` to enforce `codegraph node <Symbol>` and `codegraph impact <Symbol>` as mandatory first-stop actions before resorting to `grep_search` or `find_by_name`.
- **Strictly Decoupled Synchronization Architecture**:
  - **Fast Update (`make knowledge-sync`)**: Limited strictly to `codegraph-sync` (<2s) and `graphify-update` (<45s). Total runtime <1 minute, 0 LLM tokens. Safe to run automatically during interactive agy/opencode sessions.
  - **Full Update (`make knowledge-sync-full`)**: Aggregates `mempalace-index` (~15 min hallway graph recalculation) and `mykg-update` (Docker LLM daemon).
  - **Prohibition on Automated Full Sync**: Agent rules and hooks SHALL NOT automatically invoke `make knowledge-sync-full` or full `make mempalace-index` during interactive sessions. During sessions, only fast sync and surgical single-file mining (`mempalace mine <file>`) are permitted.

## Capabilities

### New Capabilities
- `semantic-memory-harness`: Comprehensive specification for developer and agent semantic memory services, covering executable resolution, query retrieval ergonomics, credential sanitization, session-agnostic query interfaces, and synchronization lifecycle.

### Modified Capabilities
<!-- No requirement changes to existing functional specifications. -->

## Impact

- **Developer / Agent Tooling**:
  - `.agents/skills/iqoqo-graphify/SKILL.md`
  - `.agents/skills/iqoqo-mempalace/SKILL.md`
  - `.agents/skills/iqoqo-mykg/SKILL.md` and new query script `scripts/ask.py`
  - `.agent/rules/iqoqo-standards.md`
- **Makefile**:
  - Refactored `knowledge-sync` (fast sub-minute sync: CodeGraph + Graphify only)
  - New target `knowledge-sync-full` (heavy sync: includes MemPalace index + myKG update)
  - New target `mykg-ask`
- **Developer Experience**:
  - Immediate elimination of 15-minute terminal freezes during interactive development.
- **Security & Privacy**:
  - Prevention of plaintext credentials and absolute host paths leaking into `~/.mempalace/palace/chroma.sqlite3`.
- **Token Efficiency**:
  - Estimated elimination of ~80% grep fallback loops; zero accidental LLM token consumption from automated commit syncs.
