## Why

Pre-release review of the entire iqoqo v0.7.18 codebase before beginning the 0.8.0 Federation & Semantic Web milestone. The project has grown to ~407 source files across Flask backend, Next.js frontend, Docker infrastructure, scripts, and tests. The human developer needs to reconnect with the code, and we need a systematic security/SRE/QA/architecture/readability audit to identify technical debt and risks before the next major version.

## What Changes

- **Read-only codebase review** — no code modifications, only analysis and documentation
- **26 review chunks** organized bottom-up by architectural layer (DB models → core services → API routes → strategies → utils → frontend → infra → scripts → migrations → tests)
- **Review output** persisted as markdown files in `.context/notes/review/0.7.18/` with per-file verdicts and severity-rated findings
- **Consolidated fix-plan** created after all chunks complete, feeding into a separate `review-0718-fix-plan` openspec change

## Capabilities

### New Capabilities

_None — this is a read-only review activity, not a feature change._

### Modified Capabilities

_None — no spec-level behavior changes._

## Impact

- **Output:** 26 chunk review markdown files + 1 consolidated findings document in `.context/notes/review/0.7.18/`
- **Tooling:** New `code-reviewer` skill and `code-review-partner` Gemini Gem already created
- **Follow-up:** A separate `review-0718-fix-plan` openspec change will be created after all reviews are complete
