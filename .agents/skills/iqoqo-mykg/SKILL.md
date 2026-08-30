---
name: iqoqo-mykg
description: "iqoqo-specific mykg knowledge graph indexer. Wraps mykg CLI with auto-scope discovery, multi-folder indexing, and version-aware session management. Eliminates manual CLI flag juggling."
license: AGPL
compatibility:
  - opencode
metadata:
  audience: developers
---

# Skill: iqoqo-mykg

## Purpose

This skill extends the standard `mykg` pipeline with iqoqo-specific knowledge indexing:
- **Auto-scope discovery**: Automatically determines which folders to index based on project structure and `.iqoqo-mykg-scope.yaml`
- **Multi-folder batch indexing**: Indexes `app`, `frontend`, `migrations`, `docker*`, `.context/notes/sre` in a single command
- **Session-aware operations**: Auto-detects latest mykg session; supports `index`, `update`, `grow-schema` workflows
- **No manual CLI flags**: Natural language commands map directly to correct mykg invocations

## When to Use

Trigger this skill when the user types `/iqoqo-mykg <command>` or when they need to:
- Index the entire iqoqo knowledge base (code + docs + notes)
- Update the knowledge graph after code changes
- Query the knowledge graph for architecture or implementation details

## Commands

| Command | Action |
|---------|--------|
| `/iqoqo-mykg index` | Full rebuild: all configured scopes into a fresh session |
| `/iqoqo-mykg update` | Incremental: append only changed scopes to latest session |
| `/iqoqo-mykg grow` | Grow schema: append with `--append-with-grow-schema` |
| `/iqoqo-mykg status` | Show latest session stats, indexed scopes, node/edge counts |
| `/iqoqo-mykg query "<question>"` | Query the knowledge graph |

## Workflow: Full Index (`/iqoqo-mykg index`)

### Step 1 — Detect scopes
```bash
python3 .agents/skills/iqoqo-mykg/scripts/scan_scope.py
```
- Reads `.iqoqo-mykg-scope.yaml` (or falls back to auto-detection)
- Resolves wildcards like `docker*` → `docker-compose.yml`, `docker-compose.*.yml`, `Dockerfile*`, `.dockerignore`
- Scans `.context/notes/` and `.context/ai-memory/<version>/`
- Returns ordered list of scopes to index

### Step 2 — Run extraction per scope
```bash
python3 .agents/skills/iqoqo-mykg/scripts/run_index.py
```
For each scope:
1. **First scope**: `mykg extract-graph <scope>` (creates new session)
2. **Subsequent scopes**: `mykg extract-graph <scope> --append --session <session-id>`

Scopes are processed in order:
1. `docs/` (if exists) — high-level documentation
2. `.context/notes/sre/` — SRE operational notes
3. `.context/ai-memory/<version>/` — versioned ai-memory
4. `app/` — backend code
5. `frontend/` — frontend code
6. `migrations/` — database migrations
7. `docker/` (temp dir with docker files) — infrastructure

### Step 3 — Report
```bash
python3 .agents/skills/iqoqo-mykg/scripts/get_status.py
```
Shows: session ID, indexed scopes, node/edge counts, artifact locations.

## Workflow: Incremental Update (`/iqoqo-mykg update`)

### Step 1 — Check scope changes
```bash
python3 .agents/skills/iqoqo-mykg/scripts/scan_scope.py --check
```
Compares current files against last-known manifest:
- `unchanged` → skip
- `changed: N files in M scopes` → proceed to Step 2

### Step 2 — Re-extract changed scopes
```bash
python3 .agents/skills/iqoqo-mykg/scripts/run_update.py
```
For each changed scope:
```bash
mykg extract-graph <scope> --append --session <latest-session>
```

## Workflow: Grow Schema (`/iqoqo-mykg grow`)

Same as `update`, but uses `--append-with-grow-schema` to allow the schema to evolve:
```bash
python3 .agents/skills/iqoqo-mykg/scripts/run_update.py --grow-schema
```

## Workflow: Query (`/iqoqo-mykg query "<question>"`)

```bash
mykg query "<question>" --session <latest-session>
```

## Workflow: Status (`/iqoqo-mykg status`)

```bash
python3 .agents/skills/iqoqo-mykg/scripts/get_status.py
```

Shows:
- Latest session ID and timestamp
- Indexed scopes
- Node and edge counts
- Output artifact locations

## Scope Configuration

Create `.iqoqo-mykg-scope.yaml` in project root to customize:

```yaml
# .iqoqo-mykg-scope.yaml
scopes:
  - docs
  - .context/notes/sre
  - .context/ai-memory
  - app
  - frontend
  - migrations
  - docker-compose.yml
  - docker-compose.*.yml
  - Dockerfile*
  - .dockerignore
  - deploy/
  - Makefile
  - scripts/

# Exclude patterns (applied after scope resolution)
exclude:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "**/node_modules/**"
  - "**/.git/**"
```

**Git strategy:**
- ✅ `.iqoqo-mykg-scope.yaml` — **COMMIT to git** (shared configuration)
- ❌ `.iqoqo-mykg/` — **gitignored** (runtime state: manifests, caches)

If `.iqoqo-mykg-scope.yaml` is missing, the skill auto-detects:
- `docs/` or `docs` files
- `.context/notes/*/` (selected subdirectories, excluding meta dirs)
- `.context/ai-memory/<version>/`
- `app/`, `frontend/`, `migrations/`
- Docker files (`docker-compose*.yml`, `Dockerfile*`, `.dockerignore`)
- `deploy/`, `scripts/`, `Makefile`

## File Structure

```
.opencode/skills/iqoqo-mykg/
├── SKILL.md                          # This file
└── scripts/
    ├── scan_scope.py                 # Discover and resolve scopes
    ├── run_index.py                  # Full index across all scopes
    ├── run_update.py                 # Incremental update
    └── get_status.py                 # Session status and stats
```

## Dependencies

- `mykg` CLI (already installed in `.venv/bin/mykg`)
- Python 3.14+
- `mykg_config.yaml` (already present in project root)

## Notes

- **Sessions directory**: Uses `mykg_sessions/` symlink (points to Dropbox for persistence)
- **Scope config**: `.iqoqo-mykg-scope.yaml` is committed to git; `.iqoqo-mykg/` (runtime state) is gitignored
- **Docker files**: Wildcards like `docker*` are resolved to a temporary directory before extraction
- **First run**: `index` creates a fresh session; subsequent `update`/`grow` reuse it
- **No API key?** Uses `agent-claude-code` profile by default (routes through host agent)
- **Dirty sessions?** Expected after incremental updates. The skill handles them transparently.
- **Version changes**: `.context/ai-memory/<version>/` is auto-detected from `package.json`
- **Version bump integration**: `make bump-version` automatically updates `.iqoqo-mykg-scope.yaml` and `.graphifyignore` to reference the new ai-memory version folder

## Comparison with `/mykg` Raw Harness

| Capability | Raw `/mykg` Harness | `/iqoqo-mykg` Skill |
|------------|---------------------|---------------------|
| Multi-folder indexing | Not supported | **Yes** — auto-discovers scopes |
| Auto-detect session | No | **Yes** — finds latest session |
| Natural language commands | Broken (falls through to CLI) | **Yes** — explicit command mapping |
| Incremental updates | Manual `--append` | **Yes** — `update` command |
| Schema growth | Manual `--append-with-grow-schema` | **Yes** — `grow` command |
| Status overview | Not available | **Yes** — `status` command |
| Scope configuration | None | **Yes** — `.iqoqo-mykg-scope.yaml` |

(End of file)
