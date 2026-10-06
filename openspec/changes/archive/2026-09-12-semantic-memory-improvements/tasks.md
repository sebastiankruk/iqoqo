## 1. Executable Path Determinism & Hardening

- [x] 1.1 Update `.agents/skills/iqoqo-graphify/SKILL.md` to use `.venv/bin/graphify` across all command tables and examples, and verify no bare `graphify` references remain.
- [x] 1.2 Update `.agents/skills/iqoqo-mykg/SKILL.md` to reference `.venv/bin/mykg` explicitly in all instructions and verify paths.
- [x] 1.3 Update `.agents/skills/iqoqo-mempalace/SKILL.md` to reference `.venv/bin/mempalace` explicitly and verify paths.

## 2. MemPalace Retrieval Guidelines & Ingestion Sanitization

- [x] 2.1 Add retrieval documentation in `.agents/skills/iqoqo-mempalace/SKILL.md` explaining MiniLM keyword focus, banning piping to `head` and prohibiting suppression of stderr with `2>/dev/null`.
- [x] 2.2 Implement credential and absolute path sanitization in `.agents/skills/iqoqo-mempalace/scripts/scan_scope.py` and `run_mine.py` to redact passwords, tokens, and developer paths prior to mining.
- [x] 2.3 Verify `mempalace search` execution works without errors and returns clear snippets.

## 3. Session-Agnostic myKG Query Target

- [x] 3.1 Implement `.agents/skills/iqoqo-mykg/scripts/ask.py` to auto-resolve the newest session in `mykg_sessions/` and execute `.venv/bin/mykg query "$Q"`.
- [x] 3.2 Add `mykg-ask` target in `Makefile` with argument `Q` and test `make mykg-ask Q="FRBR"` against the existing session.
- [x] 3.3 Update `.agents/skills/iqoqo-mykg/SKILL.md` documenting the new `make mykg-ask` command.

## 4. Agent Navigation Directives & Standards Enforcement

- [x] 4.1 Update `.agent/rules/iqoqo-standards.md` under CodeGraph directive to make `codegraph node` and `codegraph impact` mandatory first-stop actions before attempting raw `grep_search` or `find_by_name`.
- [x] 4.2 Document the high-ROI symbol search pattern in `.agents/skills/iqoqo-codegraph/SKILL.md` and verify rule alignment.

## 5. Decoupled Knowledge Synchronization Lifecycle

- [x] 5.1 Refactor `Makefile` knowledge targets: configure `make knowledge-sync` to run only fast engines (`codegraph-sync` and `graphify-update`) in parallel (<45s), and introduce `make knowledge-sync-full` for heavy operations (`mempalace-index` ~15m + `mykg-update`).
- [x] 5.2 Update `.agent/rules/iqoqo-standards.md` post-session memory directives: instruct agents to run `make knowledge-sync` for fast updates, allow only targeted single-file mining (`mempalace mine <file> --wing iqoqo`), and strictly forbid automated calls to `make mempalace-index` or `make knowledge-sync-full` during interactive sessions.
- [x] 5.3 Verify `make knowledge-sync` completes fast (<45s) without triggering MemPalace hallway traversal or Docker containers, and confirm `make knowledge-sync-full` syntax is valid.
