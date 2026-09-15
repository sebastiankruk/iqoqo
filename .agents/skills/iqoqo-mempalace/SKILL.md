---
name: iqoqo-mempalace
description: "iqoqo-specific MemPalace knowledge graph indexer. Wraps mempalace CLI with auto-scope discovery, dual-mode (projects + convos) indexing, and version-aware session management. Eliminates manual CLI flag juggling and prevents indexing runaway cache files."
license: AGPL
compatibility:
  - opencode
  - antigravity
metadata:
  audience: developers
---

# Skill: iqoqo-mempalace

## Purpose

This skill extends the standard `mempalace` pipeline with iqoqo-specific knowledge indexing:
- **Auto-scope discovery**: Automatically determines which folders to index based on project structure and `.iqoqo-mempalace-scope.yaml`
- **Dual-mode indexing**: Mines codebase and selected notes as projects (`--mode projects --wing iqoqo`) and current AI session transcripts as conversations (`--mode convos --wing iqoqo`)
- **Safe cache exclusion**: Explicitly skips `.mykg_sessions/` (23k+ files), cover images, and obsolete version archives
- **Unified Wing**: Ensures all drawers and entities are consistently filed under `--wing iqoqo`

## When to Use

Trigger this skill when the user types `/iqoqo-mempalace <command>` or when you need to:
- Index or synchronize the iqoqo knowledge base (code + docs + operational notes + AI memory)
- Update long-term memory after feature development or refactoring sessions
- Query historical architectural decisions and domain ontology rules

## Commands

| Command | Action | CLI Invocation |
|---------|--------|----------------|
| `/iqoqo-mempalace index` | Full rebuild | `IQOQO_AI_MODE=1 make mempalace-index` |
| `/iqoqo-mempalace update` | Incremental | `.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/run_mine.py` |
| `/iqoqo-mempalace status` | Show palace drawers & stats | `.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/get_status.py` |
| `/iqoqo-mempalace search "<query>"` | Query MemPalace memory | `.venv/bin/mempalace search "<query>" --wing iqoqo` |

## Workflow: Querying & Searching Memory (`/iqoqo-mempalace search`)

```bash
.venv/bin/mempalace search "<keywords>" --wing iqoqo
```

### Critical Retrieval Best Practices:
1. **Keyword Focus**: MemPalace utilizes MiniLM semantic embeddings. Use tight 2-4 word concept keywords (e.g. `"FRBR board games"`, `"OpenRouter routing"`, `"ActivityPub actor"`) rather than conversational multi-sentence queries.
2. **Never Pipe to `head`**: MemPalace outputs room and drawer headers before the matching text snippets. Piping to `head -30` truncates the actual content. Let the CLI output flow or inspect matches in full.
3. **Never Swallow `stderr` (`2>/dev/null`)**: Do NOT silence stderr. Silencing stderr swallows critical diagnostic messages (e.g. collection missing, lock conflicts) that tell you why an answer was not found.

## Workflow: Full Index (`/iqoqo-mempalace index` or `make mempalace-index`)

> [!WARNING]
> Full palace indexing walks 297k+ entity links in its hallway graph and takes ~15 minutes on CPU. Do NOT run full indexing automatically during interactive sessions. Use surgical targeted mining instead.

### Step 1 — Detect scopes
```bash
.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/scan_scope.py
```
- Reads `.iqoqo-mempalace-scope.yaml`
- Resolves codebase directories (`app`, `frontend`, `migrations`, `deploy`, `scripts`, `shared`, `tests`, `docs`, `openspec/specs`)
- Resolves selected Obsidian notes (`.context/notes/{sre,bugs,code,design,dev,marketing,plan,review,security,tests,tools,notes}`)
- Auto-detects current version from `package.json` for `.context/ai-memory/<version>`
- Strictly excludes `.mykg_sessions/`, `app/static/covers/`, `screenshots/`, and non-current versions

### Step 2 — Run mining
```bash
.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/run_mine.py
```
- Mines project scopes with `.venv/bin/mempalace mine <scope> --mode projects --wing iqoqo`
- Mines conversation memory with `.venv/bin/mempalace mine .context/ai-memory/<version> --mode convos --wing iqoqo`

### Step 3 — Report status
```bash
.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/get_status.py
```

## Workflow: Targeted Mining (Fast Single-File Ingestion, ~1-2s)

To mine a specific file or directory after making changes during interactive sessions:
```bash
.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/run_mine.py <path>
```
Or directly:
```bash
.venv/bin/mempalace mine <path> --wing iqoqo
```

## Scope Configuration

Customized via `.iqoqo-mempalace-scope.yaml` in the project root:

```yaml
scopes:
  - docs
  - openspec/specs
  - .context/notes/sre
  - .context/notes/bugs
  - .context/notes/code
  - .context/notes/design
  - .context/notes/dev
  - .context/notes/marketing
  - .context/notes/openspec
  - .context/notes/plan
  - .context/notes/review
  - .context/notes/security
  - .context/notes/tests
  - .context/notes/tools
  - .context/notes/notes
  - app
  - frontend
  - migrations
  - deploy
  - scripts
  - shared
  - tests
  - Makefile
  - docker-compose.yml
  - docker-compose.prod.yml

convos_scopes:
  - .context/ai-memory

exclude:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "**/node_modules/**"
  - "**/.git/**"
  - "**/.next/**"
  - "**/.venv/**"
  - "**/app/static/covers/**"
  - "**/app/static/gallery/**"
  - "**/mykg_sessions/**"
  - "**/.mykg_sessions/**"
  - "**/screenshots/**"
  - "**/images/**"
```

## File Structure

```
.agents/skills/iqoqo-mempalace/
├── SKILL.md                          # This file
└── scripts/
    ├── scan_scope.py                 # Discover and resolve scopes
    ├── run_mine.py                   # Execute scoped mining
    └── get_status.py                 # Show palace stats
```
