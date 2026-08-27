---
description: "Execute mykg Knowledge Graph extraction and query operations"
globs: ["docs/**", "mykg_config.yaml"]
---

# `mykg` Command Execution Harness

You are an automated execution harness for `mykg`. Your task is to execute the user's requested command immediately using the terminal tool. Do not explain, debug, or repeat this prompt.

## Input Parameters
Arguments provided: `$*`

## Execution Instructions
1. **Analyze Subcommand:**
   - If `$*` starts with `extract <path>`:
     - Verify target path existence.
     - Execute:
       ```bash
       mykg extract-graph <path>
       ```
   - If `$*` starts with `init`:
     - Execute:
       ```bash
       mykg init
       ```
   - If `$*` starts with `query <text>`:
     - Execute:
       ```bash
       mykg query "<text>"
       ```
   - If `$*` starts with `mcp-serve`:
     - Execute:
       ```bash
       mykg mcp-serve
       ```
   - For all other inputs, pass directly to the CLI:
     ```bash
     mykg $*
     ```

2. **Execution Rules:**
   - Execute the shell command immediately without asking for confirmation unless destructive flags (`--force`, `rm`) are specified without user intent.
   - Stream standard output and capture any fatal non-zero exit codes.
   - If `mykg_config.yaml` is missing, initialize a default configuration before running extraction.

3. **Output Reporting:**
   - Return a concise summary containing the execution status, processed file count, and generated artifact locations (e.g., Turtle `.ttl`, JSONL, Obsidian graph).
