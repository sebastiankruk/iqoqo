## 1. Daemon Implementation

- [x] 1.1 Create `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py` and verify it parses command line arguments (inbox and outbox paths) correctly.
- [x] 1.2 Implement the `ThreadPoolExecutor` loop in `agy_daemon.py` to watch the inbox and invoke `agy -p` subprocesses, verifying it writes the JSON answer and `.done` sentinel successfully.

## 2. Skill Modification

- [x] 2.1 Update `.agents/skills/iqoqo-mykg/SKILL.md` to remove the manual watch loop (Stage 4a) and subagent prompt templates, replacing them with a simple directive to run `IQOQO_AI_MODE=1 make mykg-update` in the background. Verify the markdown diff accurately reflects the simplification.

## 3. Makefile & Orchestration Update

- [x] 3.1 Update `Makefile` to include the new `mykg-update` target, ensuring it launches `agy_daemon.py` within the `python:3.11-slim` Docker container and mounts only the `.agents` and `mykg_sessions` directories. Verify by inspecting the printed docker command during a dry-run or syntax check.
- [x] 3.2 Add the `knowledge-sync` target in `Makefile` to chain `codegraph-sync`, `mempalace-index`, and `mykg-update`. Verify the target executes without syntax errors.

## 4. Bug Fixes

- [x] 4.1 Update `.agents/skills/iqoqo-mykg/scripts/run_update.py` to detect if the scope contains a list of files rather than a directory, wrapping them in a temporary directory before calling `mykg extract-graph`. Verify the python syntax and logic.
