# Technical Design: Semantic Memory & Developer Tooling Improvements

## Context

See `proposal.md` and telemetry note `.context/notes/notes/memtools-optimizing-automated-update.md`. Empirical telemetry revealed that:
- `codegraph sync` takes **0.2 to 1.5 seconds**.
- `make graphify-update` takes **15 to 45 seconds**.
- `make mempalace-index` takes **~15 minutes (900–930 seconds)** every run, recalculating 297,397 within-wing entity links in its hallway graph on CPU even when 0 files changed.
- `mykg-update` runs multi-batch LLM extraction inside Docker across hours.

Previously, `make knowledge-sync` coupled `mempalace-index` into the parallel developer sync target. Sitting in front of the terminal waiting 15 solid minutes for MemPalace during interactive agent sessions introduces massive friction.

## Goals / Non-Goals

**Goals:**
- Eliminate `command not found (127)` subshell errors across all memory skill commands.
- Provide a zero-friction, session-agnostic query interface for myKG (`make mykg-ask Q="..."`).
- Document optimal retrieval practices for MemPalace (MiniLM keyword density, stderr preservation).
- Implement a pre-mining credential and absolute path sanitization stage for MemPalace.
- Enforce CodeGraph as the mandatory first-stop symbol inspection tool in `.agent/rules/iqoqo-standards.md`.
- **Strictly decouple fast sub-minute indexing (`codegraph` + `graphify`) from multi-minute batch operations (`mempalace` + `mykg`) in `Makefile` and agent directives**.
- **Prohibit automated execution of full sync (`make knowledge-sync-full` or `make mempalace-index`) during interactive agy/opencode sessions**.

**Non-Goals:**
- Modifying the underlying algorithms of external CLI tools (ChromaDB, tree-sitter, Graphify, or myKG core).
- Removing the Docker sandbox for myKG (security isolation must remain intact).
- Automatic re-indexing of historical sessions already in git or archives.

## Decisions

### Decision 1: Deterministic Virtualenv Execution Over Global PATH Reliance
- **Choice**: Hardcode `.venv/bin/<executable>` in all skill command examples, CLI tables, and internal wrapper scripts (e.g. `.venv/bin/graphify`, `.venv/bin/mykg`, `.venv/bin/mempalace`).
- **Rationale**: Agents and subshells do not consistently inherit activated virtual environments. Hardcoding the project virtualenv path guarantees zero PATH drift.
- **Alternatives Considered**: Modifying global shell rc files or relying on `which` fallbacks (fragile across environments).

### Decision 2: Session-Agnostic myKG Query Script (`scripts/ask.py`)
- **Choice**: Create `.agents/skills/iqoqo-mykg/scripts/ask.py` and a corresponding `make mykg-ask Q="..."` target. The script auto-resolves the newest session directory from `mykg_sessions/` and runs `.venv/bin/mykg query "$Q" --session <latest_id>`.
- **Rationale**: Telemetry proved agents failed to query myKG because they had to manually run `ls mykg_sessions/` to discover session UUIDs/timestamps.
- **Alternatives Considered**: Expecting the agent to remember the session name or maintaining a `.latest_session` symlink.

### Decision 3: Sanitization Pre-Filter for MemPalace Ingestion
- **Choice**: Add sanitization routines to `.agents/skills/iqoqo-mempalace/scripts/scan_scope.py` and `run_mine.py`. Before feeding file chunks into `mempalace mine`, match and redact known credential patterns (`PASSWORD=...`, `SECRET=...`, `API_KEY=...`) and normalize developer absolute paths (e.g. `/home/sebastiankruk/Development/iqoqo` -> `.`).
- **Rationale**: Prevents accidental leakage of host secrets and absolute user directories into `chroma.sqlite3`.
- **Alternatives Considered**: Post-processing the 2.1 GB SQLite database (fragile and slow).

### Decision 4: Tiered Knowledge Synchronization (Fast vs Full) & Automated Call Restrictions
- **Choice**:
  - `make knowledge-sync` (Fast Update): Runs `memory-presync`, `codegraph-sync`, and `graphify-update` in parallel. Total runtime: ~15-45 seconds, 0 LLM tokens. This is the **only** target permitted to run automatically or be recommended post-task during interactive agy/opencode sessions.
  - `make knowledge-sync-full` (Full Pipeline): Runs the fast sync plus `mempalace-index` (~15 min hallway calculation) and `mykg-update` (Docker LLM daemon). Only invoked manually or during scheduled release CI pipelines.
  - **Single-File MemPalace Exception**: If an agent modifies a specific domain document and needs persistent memory indexing, it may invoke surgical single-file mining (`mempalace mine <file> --wing iqoqo`), which executes in ~1-2 seconds without triggering the 15-minute hallway recalculation.
- **Rationale**: Telemetry proved `make mempalace-index` takes ~15 minutes even with 0 new files due to 297k entity hallway links on CPU. Coupling it into `knowledge-sync` paralyzes interactive development.
- **Alternatives Considered**: Retaining MemPalace in `knowledge-sync` with a timeout (causes partial/corrupted indexes).

### Decision 5: CodeGraph First-Stop Directive in Agent Rules
- **Choice**: Update `.agent/rules/iqoqo-standards.md` under the CodeGraph directive with mandatory instructions: before executing `grep_search` or `find_by_name` for any code symbol (class, function, model, route), the agent MUST run `codegraph node <Symbol>` or `codegraph impact <Symbol>`.
- **Rationale**: Telemetry demonstrated a 0% fallback rate for CodeGraph, but agents under-utilized it in favor of brute-force text grep.

## Risks / Trade-offs

- **[Risk] Developer expects MemPalace to update during `make knowledge-sync`**  
  → *Mitigation*: The output of `make knowledge-sync` clearly states: *"Fast knowledge sync complete (CodeGraph + Graphify). MemPalace & myKG full sync deferred to 'make knowledge-sync-full'."*
- **[Risk] Regex sanitization in MemPalace strips valid code examples**  
  → *Mitigation*: Scope credential regexes strictly to assignment structures in config/env files and note headers, avoiding broad keyword wipes in source code.
