---
name: iqoqo-graphify
description: "iqoqo-specific knowledge graph indexer. Wraps graphify with custom semantic extraction for .context/ notes and ai-memory. No API key required — routes LLM extraction through the host agent."
license: AGPL
compatibility:
  - opencode
metadata:
  audience: developers
---

# Skill: iqoqo-graphify

## Purpose

This skill extends the standard graphify pipeline with iqoqo-specific knowledge indexing:
- **Version-aware context indexing**: `.context/notes/` + `.context/ai-memory/<current-version>/`
- **Inline LLM semantic extraction**: No API key required — routes through the host agent
- **Auto-trigger at session end**: After commit/push, agents recommend running the sync

## When to Use

Trigger this skill when the user types `/iqoqo-graphify <command>` or when codebase questions arise that could benefit from the knowledge graph.

## Commands

| Command | Action |
|---------|--------|
| `/iqoqo-graphify index` | Full rebuild: `IQOQO_AI_MODE=1 make graphify-index` |
| `/iqoqo-graphify update` | Incremental: `IQOQO_AI_MODE=1 make graphify-update` |
| `/iqoqo-graphify query "<question>"` | Query the graph: `.venv/bin/graphify query "<question>"` |
| `/iqoqo-graphify status` | Show graph stats: `make graphify-status` |

## Execution Architecture

The skill wraps all graphify AST code indexing and `.context/` semantic entity extraction into unified, non-interactive Makefile and runner targets:
- `make graphify-update`: Runs `run_update.py` to incrementally update changed code files via AST, scans `.context/`, extracts markdown semantic entities, merges graphs, and regenerates community clusters without requiring multiple approval prompts.
- `make graphify-index`: Runs `run_index.py` for a full clean rebuild.
- `make graphify-status`: Runs `get_status.py` to report current graph nodes, edges, and communities.

## Workflow: Full Index (`/iqoqo-graphify index`)

```bash
IQOQO_AI_MODE=1 make graphify-index
```
1. Detects current version from `package.json`
2. Extracts code AST (`.venv/bin/graphify extract . --code-only`)
3. Scans `.context/notes/` and `.context/ai-memory/<version>/`
4. Extracts semantic entities and relationships from markdown chunks
5. Merges AST + semantic extractions into `graphify-out/graph.json`
6. Re-clusters graph communities and updates report & visualization

## Workflow: Incremental Update (`/iqoqo-graphify update`)

```bash
IQOQO_AI_MODE=1 make graphify-update
```
1. Updates code graph incrementally via AST (`.venv/bin/graphify update .`)
2. Compares `.context/` manifests for changed files
3. Re-extracts only changed markdown chunks
4. Merges into unified graph and rebuilds community visualizations

## Workflow: Query (`/iqoqo-graphify query "<question>"`)

```bash
.venv/bin/graphify query "<question>"
```

Or with options:
```bash
.venv/bin/graphify query "<question>" --dfs --budget 3000
```

## Workflow: Status (`/iqoqo-graphify status`)

```bash
make graphify-status
```

## Integration with Agent Rules

The `iqoqo-standards.md` rule file contains the agent-facing directive:
- Agents RECOMMEND using graphify for codebase questions
- Agents RECOMMEND running sync after commit/push (`make knowledge-sync` or `make graphify-update`)
- Version-scoped ai-memory is managed automatically

## File Structure

```
.agents/skills/iqoqo-graphify/
├── SKILL.md                          # This file
└── scripts/
    ├── run_update.py                 # Autonomous incremental update runner
    ├── run_index.py                  # Autonomous full index builder
    ├── get_status.py                 # Graph stats and status reporter
    ├── get_version.py                # Read version from package.json
    ├── scan_context.py               # Scan .context/ with .graphifyignore
    ├── extract_semantic.py           # Extract entities from markdown chunks
    └── merge_semantic.py             # Merge chunk JSONs
```

## Dependencies

- `graphify` CLI (installed in `.venv/bin/graphify`)
- Python 3.14+
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` (optional — enables fast native extraction)

## Notes

- **Single command execution**: All sub-steps run autonomously within `make graphify-update` / `make graphify-index`.
- **Dirty graph files?** Expected after hooks or incremental updates. The skill handles them transparently.
- **Version changes**: `make bump-version` automatically updates `.graphifyignore` to exclude the old version's ai-memory folder. The current version is auto-detected from `package.json`. Re-run `/iqoqo-graphify index` after bumping.
