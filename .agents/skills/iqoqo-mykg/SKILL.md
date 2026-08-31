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
| `/iqoqo-mykg index` | Full rebuild: `IQOQO_AI_MODE=1 make mykg-index` |
| `/iqoqo-mykg update` | Incremental update: `IQOQO_AI_MODE=1 make mykg-update` |
| `/iqoqo-mykg grow` | Grow schema: `IQOQO_AI_MODE=1 make mykg-update ARGS="--grow-schema"` |
| `/iqoqo-mykg status` | Show latest session stats: `make mykg-status` |
| `/iqoqo-mykg query "<question>"` | Query the knowledge graph |

## Execution Architecture

myKG uses the `agent-claude-code` profile to preserve data sovereignty (keeping all LLM operations within the local Antigravity opencode session without routing through untrusted APIs).

To avoid UI prompt fatigue and preserve host security:
- The task processing daemon (`agy_daemon.py`) runs in the background inside a strictly sandboxed Docker container (`python:3.11-slim`).
- Only `mykg_sessions` is mounted read-write, while `.agents` is mounted read-only. The rest of the host workspace is isolated.
- The `make mykg-update` and `make mykg-index` targets automatically start this daemon, run the scope extractions, and cleanly terminate the daemon upon completion.

## File Structure

```
.agents/skills/iqoqo-mykg/
├── SKILL.md                          # This file
└── scripts/
    ├── agy_daemon.py                 # Sandboxed task processing daemon
    ├── scan_scope.py                 # Discover and resolve scopes
    ├── run_index.py                  # Full index across all scopes
    ├── run_update.py                 # Incremental update
    └── get_status.py                 # Session status and stats
```

## Dependencies

- `mykg` CLI (already installed in `.venv/bin/mykg`)
- Python 3.14+
- Docker (for sandboxed background task daemon)
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
