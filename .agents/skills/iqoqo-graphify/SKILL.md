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
| `/iqoqo-graphify index` | Full rebuild: code (AST) + .context (semantic) |
| `/iqoqo-graphify update` | Incremental: only changed files |
| `/iqoqo-graphify query "<question>"` | Query the graph |
| `/iqoqo-graphify status` | Show graph stats + indexed scopes |

## Workflow: Full Index (`/iqoqo-graphify index`)

### Step 1 — Detect version
```bash
python3 .agents/skills/iqoqo-graphify/scripts/get_version.py
```
Reads `package.json` → returns current version (e.g., `0.7.17`).

### Step 2 — Scan .context/
```bash
python3 .agents/skills/iqoqo-graphify/scripts/scan_context.py
```
- Reads `.graphifyignore`
- Scans `.context/notes/` and `.context/ai-memory/<version>/`
- Returns list of markdown files to process
- Writes chunk manifests to `graphify-out/.iqoqo_chunks/`

### Step 3 — Semantic extraction (if no API key)

If `GEMINI_API_KEY` or `GOOGLE_API_KEY` is NOT set:

1. Split files into chunks of ~20 files each
2. For each chunk, read files and extract entities/relationships using the standard graphify extraction prompt
3. Write results to `graphify-out/.graphify_chunk_NN.json`

**Extraction prompt** (from `references/extraction-spec.md`):
- EXTRACTED: relationship explicit in source
- INFERRED: reasonable inference
- AMBIGUOUS: uncertain — flag for review
- Node IDs: lowercase, `[a-z0-9_]`, full repo-relative path
- Include `source_file` verbatim

### Step 4 — Merge semantic chunks
```bash
python3 .agents/skills/iqoqo-graphify/scripts/merge_semantic.py
```
- Reads `graphify-out/.graphify_chunk_*.json`
- Deduplicates nodes by ID
- Writes `graphify-out/.graphify_semantic.json`

### Step 5 — AST extraction (code)
```bash
graphify extract . --code-only
```
Or native full extraction if API key is available:
```bash
graphify extract . --mode deep
```

### Step 6 — Merge and build
```bash
python3 -c "
import json
from pathlib import Path

ast = json.loads(Path('graphify-out/.graphify_ast.json').read_text())
sem = json.loads(Path('graphify-out/.graphify_semantic.json').read_text())

seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged = {
    'nodes': merged_nodes,
    'edges': ast['edges'] + sem['edges'],
    'hyperedges': sem.get('hyperedges', []),
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, indent=2))
print(f'Merged: {len(merged_nodes)} nodes, {len(merged[\"edges\"])} edges')
"
```

### Step 7 — Cluster and report
```bash
graphify cluster-only . --no-label
```

## Workflow: Incremental Update (`/iqoqo-graphify update`)

This command updates **both** code (current directory) and `.context/` knowledge incrementally.

### Step 1 — Update code graph
```bash
graphify update .
```
- Detects new/changed/deleted files in the current directory automatically
- Runs AST extraction only on changed files
- Fast, no API cost

### Step 2 — Check `.context/` for changes
```bash
python3 .agents/skills/iqoqo-graphify/scripts/scan_context.py --check
```
- Compares current `.context/` files against last-known manifest
- Returns:
  - `unchanged` → skip to Step 5 (merge only)
  - `changed: N files in M chunks` → proceed to Step 3

### Step 3 — Incremental semantic extraction (if `.context/` changed)

Only re-extract changed chunks:

1. Load previous chunk manifests from `graphify-out/.iqoqo_chunks/`
2. Compare file mtimes against previous scan
3. Identify changed chunks
4. Re-extract only changed chunks via inline LLM
5. Write updated chunks to `graphify-out/.graphify_chunk_NN.json`

### Step 4 — Incremental semantic merge
```bash
python3 .agents/skills/iqoqo-graphify/scripts/merge_semantic.py --incremental
```
- Loads existing `.graphify_semantic.json`
- Replaces nodes/edges from changed chunks
- Keeps unchanged chunks as-is
- Writes updated `.graphify_semantic.json`

### Step 5 — Merge AST + semantic
```bash
python3 -c "
import json
from pathlib import Path

ast = json.loads(Path('graphify-out/.graphify_ast.json').read_text())
sem = json.loads(Path('graphify-out/.graphify_semantic.json').read_text())

seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged = {
    'nodes': merged_nodes,
    'edges': ast['edges'] + sem['edges'],
    'hyperedges': sem.get('hyperedges', []),
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, indent=2))
print(f'Merged: {len(merged_nodes)} nodes, {len(merged[\"edges\"])} edges')
"
```

### Step 6 — Cluster and report
```bash
graphify cluster-only . --no-label
```

**Result**: Code + `.context/` are both updated incrementally in one command.

## Workflow: Query (`/iqoqo-graphify query "<question>"`)

```bash
graphify query "<question>"
```

Or with options:
```bash
graphify query "<question>" --dfs --budget 3000
```

## Integration with Agent Rules

The `iqoqo-standards.md` rule file contains the agent-facing directive:
- Agents RECOMMEND using graphify for codebase questions
- Agents RECOMMEND running sync after commit/push
- Version-scoped ai-memory is managed automatically

## File Structure

```
.agents/skills/iqoqo-graphify/
├── SKILL.md                          # This file
└── scripts/
    ├── get_version.py                # Read version from package.json
    ├── scan_context.py               # Scan .context/ with .graphifyignore
    └── merge_semantic.py             # Merge chunk JSONs
```

## Dependencies

- `graphify` CLI (already installed)
- Python 3.14+
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` (optional — enables fast native extraction)

## Notes

- **No API key?** The skill falls back to inline LLM extraction through the host agent. This is slower but requires no external API.
- **Dirty graph files?** Expected after hooks or incremental updates. The skill handles them transparently.
- **Version changes**: `make bump-version` automatically updates `.graphifyignore` to exclude the old version's ai-memory folder. The current version is auto-detected from `package.json`. Re-run `/iqoqo-graphify index` after bumping.
