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

| Command | Action |
|---------|--------|
| `/iqoqo-mempalace index` | Full rebuild: all configured scopes and AI memory into `--wing iqoqo` |
| `/iqoqo-mempalace update` | Incremental: mine changed files or specific scopes |
| `/iqoqo-mempalace status` | Show palace drawers, room distributions, and stats |
| `/iqoqo-mempalace search "<query>"` | Query MemPalace memory |

## Workflow: Full Index (`/iqoqo-mempalace index` or `make mempalace-index`)

### Step 1 — Detect scopes
```bash
python3 .agents/skills/iqoqo-mempalace/scripts/scan_scope.py
```
- Reads `.iqoqo-mempalace-scope.yaml`
- Resolves codebase directories (`app`, `frontend`, `migrations`, `deploy`, `scripts`, `shared`, `tests`, `docs`, `openspec/specs`)
- Resolves selected Obsidian notes (`.context/notes/{sre,bugs,code,design,dev,marketing,plan,review,security,tests,tools,notes}`)
- Auto-detects current version from `package.json` for `.context/ai-memory/<version>`
- Strictly excludes `.mykg_sessions/`, `app/static/covers/`, `screenshots/`, and non-current versions

### Step 2 — Run mining
```bash
python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py
```
- Mines project scopes with `mempalace mine <scope> --mode projects --wing iqoqo`
- Mines conversation memory with `mempalace mine .context/ai-memory/<version> --mode convos --wing iqoqo`

### Step 3 — Report status
```bash
python3 .agents/skills/iqoqo-mempalace/scripts/get_status.py
```

## Workflow: Targeted Mining

To mine a specific file or directory after making changes:
```bash
python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py <path>
```
Or directly:
```bash
mempalace mine <path> --wing iqoqo
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
