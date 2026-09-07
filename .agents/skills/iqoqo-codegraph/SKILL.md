---
name: iqoqo-codegraph
description: "iqoqo-specific CodeGraph intelligence and symbol dependency mapping. Wraps codegraph CLI for instant symbol search, impact analysis, caller/callee tracing, and pre-refactor blast radius assessment."
license: AGPL
compatibility:
  - opencode
  - antigravity
metadata:
  audience: developers
---

# Skill: iqoqo-codegraph

## Purpose

This skill provides code intelligence and AST-level symbol dependency mapping for the iQoQo codebase using the standalone `codegraph` CLI:
- **Instant symbol sync**: Incremental scanning via `codegraph sync` (<0.2s)
- **Blast radius analysis**: Trace impacted routes, models, and UI hooks with `codegraph impact <Symbol>`
- **Multi-symbol exploration**: Explore symbols, call paths, and source definitions with `codegraph explore "<query>"`
- **Affected test discovery**: Identify test files affected by source modifications with `codegraph affected <files...>`
- **Call hierarchy traversal**: Inspect callers and callees with `codegraph callers <symbol>` / `codegraph callees <symbol>`

## When to Use

Trigger this skill when the user types `/iqoqo-codegraph <command>` or during development:
- **OpenSpec Explore Phase**: Before proposing changes to SQLAlchemy models, Flask routes, or React hooks, run `codegraph impact <SymbolName>` to assess ripple effects.
- **Post-Commit Knowledge Sync**: After structural code edits, run `codegraph sync` (or `make codegraph-sync`).
- **Targeted Testing**: Run `codegraph affected <file>` to know which tests to execute first.

## Commands

| Command | Action | CLI Invocation |
|---------|--------|----------------|
| `/iqoqo-codegraph sync` | Incremental symbol sync | `codegraph sync` |
| `/iqoqo-codegraph index` | Rebuild full AST symbol index | `codegraph index` |
| `/iqoqo-codegraph status` | Show symbol count and language stats | `codegraph status` |
| `/iqoqo-codegraph impact <symbol>` | Analyze code affected by changing symbol | `codegraph impact <symbol>` |
| `/iqoqo-codegraph explore "<query>"` | View relevant symbols and call paths | `codegraph explore "<query>"` |
| `/iqoqo-codegraph node <symbol>` | Show symbol source and caller/callee trail | `codegraph node <symbol>` |
| `/iqoqo-codegraph callers <symbol>` | Find all functions that call symbol | `codegraph callers <symbol>` |
| `/iqoqo-codegraph callees <symbol>` | Find all functions called by symbol | `codegraph callees <symbol>` |
| `/iqoqo-codegraph affected <files...>` | Find test files affected by changed files | `codegraph affected <files...>` |

## Workflow Examples

### Assessing Impact Before Refactoring
```bash
codegraph impact Manifestation
```
Shows dependent models, API serializers, scanner strategies, and UI interfaces directly impacted by changes to `Manifestation`.

### Finding Callers of a Function
```bash
codegraph callers parse_barcode
```

### Finding Affected Tests
```bash
codegraph affected app/api/scanner.py
```

### Post-Change Sync
```bash
make codegraph-sync
# or: codegraph sync
```
