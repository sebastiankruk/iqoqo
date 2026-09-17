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
- **Mandatory First-Stop Symbol Navigation**: Before running `grep_search`, `find_by_name`, or ripgrep for any code symbol (class, function, method, SQLAlchemy model, Flask route, or React hook), execute CodeGraph first. It returns exact AST references without grep noise (<0.2s).
- **OpenSpec Explore Phase**: Before proposing changes to SQLAlchemy models, Flask routes, or React hooks, run `codegraph impact <SymbolName>` to assess ripple effects.
- **Post-Commit Knowledge Sync**: After structural code edits, run `codegraph sync` (or `make codegraph-sync`).
- **Targeted Testing**: Run `codegraph affected <file>` to know which tests to execute first.

## Commands

| Command | Action | CLI Invocation |
|---------|--------|----------------|
| `/iqoqo-codegraph sync` | Incremental symbol sync | `codegraph sync` |
| `/iqoqo-codegraph index` | Rebuild full AST symbol index | `codegraph index` |
| `/iqoqo-codegraph status` | Show symbol count and language stats | `codegraph status` |
| `/iqoqo-codegraph query "<search>"` | Search symbols, routes, partial names | `codegraph query "<search>"` |
| `/iqoqo-codegraph impact <symbol>` | Analyze code affected by changing symbol | `codegraph impact <symbol>` |
| `/iqoqo-codegraph explore "<query>"` | View relevant symbols and call paths | `codegraph explore "<query>"` |
| `/iqoqo-codegraph node <symbol>` | Show symbol source and caller/callee trail | `codegraph node <symbol>` |
| `/iqoqo-codegraph node -f <file> <symbol>` | Disambiguate multi-definition symbol | `codegraph node -f <file> <symbol>` |
| `/iqoqo-codegraph callers <symbol>` | Find all functions that call symbol | `codegraph callers <symbol>` |
| `/iqoqo-codegraph callees <symbol>` | Find all functions called by symbol | `codegraph callees <symbol>` |
| `/iqoqo-codegraph affected <files...>` | Find test files affected by changed files | `codegraph affected <files...>` |

## High-ROI Symbol Search Pattern

When investigating unfamiliar code or tracking down a symbol, follow this 4-step navigation sequence instead of grepping:

1. **Discover & Search Routes or Partial Names**:
   ```bash
   codegraph query "<SearchTerm>"
   ```
   Finds route decorators (e.g. `codegraph query "items/bulk"`), React hooks (e.g. `useManifestation`), or fuzzy symbol names without needing the exact identifier.

2. **Inspect Definition & Context**:
   ```bash
   codegraph node <SymbolName>
   # When defined in multiple places (e.g. Python class vs React component):
   codegraph node -f <filename> <SymbolName>
   ```
   Instantly displays the symbol declaration, file path, line numbers, docstring, and immediate caller/callee list without drowning in string search hits.

3. **Assess Blast Radius & Ripple Effects**:
   ```bash
   codegraph impact <SymbolName>
   ```
   Maps all downstream dependents (routes, models, controllers, UI components) that depend on this symbol.

4. **Trace Call Hierarchies**:
   ```bash
   codegraph callers <SymbolName>
   codegraph callees <SymbolName>
   ```
   Traces upstream callers and downstream callees across the entire repository.

## Repository Scope & Cross-Boundary Architecture

CodeGraph indexes the entire repository across both languages:
- **Backend**: Python/Flask models, routes, services (`app/**`, `tests/**`)
- **Frontend**: Next.js App Router components, React hooks, utilities (`frontend/**`)

> [!NOTE]
> HTTP client calls in frontend (`apiClient.post("/items/bulk")`) and Flask route handlers (`@api_bp.route("/items/bulk")`) do not share static AST edges across languages. To discover endpoints, always use `codegraph query "<route_path>"` rather than `codegraph node`.

## Workflow Examples

### Assessing Impact Before Refactoring
```bash
codegraph impact Manifestation
```
Shows dependent models, API serializers, scanner strategies, and UI interfaces directly impacted by changes to `Manifestation`.

### Inspecting a Symbol Definition
```bash
codegraph node parse_barcode
```

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
