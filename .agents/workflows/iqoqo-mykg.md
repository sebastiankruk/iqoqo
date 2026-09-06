---
description: "iqoqo-specific mykg knowledge graph indexer with auto-scope discovery and multi-folder indexing"
globs: ["docs/**", "mykg_config.yaml", ".iqoqo-mykg-scope.yaml"]
---

# `iqoqo-mykg` Command Execution Harness

You are an automated execution harness for the `iqoqo-mykg` skill. This wraps the raw `mykg` CLI with iqoqo-specific scope discovery, multi-folder batching, and session management.

**DO NOT** pass natural language directly to `mykg`. Always map commands through the scripts below.

## Input Parameters
Arguments provided: `$*`

## Execution Instructions

1. **Analyze Subcommand:**
   - If `$*` starts with `index`:
     - Step 1: Discover scopes
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/scan_scope.py
       ```
     - Step 2: Run full index
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/run_index.py
       ```
   - If `$*` starts with `update`:
     - Step 1: Check for changes
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/scan_scope.py --check
       ```
     - Step 2: Run incremental update
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/run_update.py
       ```
   - If `$*` starts with `grow`:
     - Step 1: Check for changes
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/scan_scope.py --check
       ```
     - Step 2: Run grow schema
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/run_update.py --grow-schema
       ```
   - If `$*` starts with `status`:
     - Execute:
       ```bash
       python3 .agents/skills/iqoqo-mykg/scripts/get_status.py
       ```
   - If `$*` starts with `query <text>`:
     - Auto-detect latest session and execute:
       ```bash
       python3 -c "
       import subprocess
       from pathlib import Path
       sessions_dir = Path('mykg_sessions') if Path('mykg_sessions').exists() else Path('.mykg_sessions')
       if sessions_dir.exists():
           sessions = [(item.name, item.stat().st_mtime) for item in sessions_dir.iterdir() if item.is_dir()]
           sessions.sort(key=lambda x: x[1], reverse=True)
           session = sessions[0][0] if sessions else None
       else:
           session = None
       if session:
           subprocess.run(['.venv/bin/mykg', 'query', '$*'.replace('query ', '', 1), '--session', session])
       else:
           print('No session found. Run index first.')
       "
       ```
   - For all other inputs that look like natural language (contain words like "append", "grow", "schema", "from"):
     - **DO NOT** pass to raw CLI. Instead, interpret intent:
       - If contains "grow" or "expand" → treat as `grow`
       - If contains "append" or "update" → treat as `update`
       - If contains "index" or "rebuild" → treat as `index`
       - Otherwise → ask user to clarify
   - For truly unrecognized inputs:
     - Pass to raw CLI:
       ```bash
       .venv/bin/mykg $*
       ```

2. **Execution Rules:**
   - Execute the shell command immediately without asking for confirmation unless destructive flags (`--force`, `rm`, `--delete-session`) are specified without user intent.
   - Stream standard output and capture any fatal non-zero exit codes.
   - If `mykg_config.yaml` is missing, run `.venv/bin/mykg init` first.

3. **Output Reporting:**
   - Return a concise summary containing: execution status, indexed scopes, session ID, node/edge counts, and artifact locations.

## Scope Configuration

The `.iqoqo-mykg-scope.yaml` file in project root defines which folders to index.

**Git strategy:**
- ✅ `.iqoqo-mykg-scope.yaml` — **COMMIT to git** (shared configuration)
- ❌ `.iqoqo-mykg/` — **gitignored** (runtime state: manifests, caches)

If the config file is missing, auto-discovery runs. Create the config file to have explicit, version-controlled control over indexed scopes.

## Common Natural Language Mappings

| User Input | Mapped Command | Action |
|------------|----------------|--------|
| `append and grow schema from app, frontend, migrations, docker*` | `grow` | `--append-with-grow-schema` on changed scopes |
| `index app, frontend, migrations, docker*` | `index` | Full rebuild of specified scopes |
| `update the knowledge graph` | `update` | Incremental append of changed scopes |
| `what's the status?` | `status` | Show session stats |
| `query how does auth work?` | `query` | Query latest session |

(End of file)
