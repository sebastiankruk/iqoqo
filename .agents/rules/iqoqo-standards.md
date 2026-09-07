---
trigger: always_on
description: "Global coding standards and architectural rules for the iqoqo project."
---

Talk like caveman

### 🏰 MemPalace CLI Memory & Entity Alignment Directive
- **Context Awareness**: Long-term episodic memory and architectural decisions are indexed locally via the standalone `mempalace` CLI utility. Do NOT look for MCP memory tools.
- **Pre-Flight Querying (CLI)**: Before analyzing architectural debt or implementing new domain features, you RECOMMEND executing a shell query in your terminal to retrieve historical engineering decisions:
  `mempalace search "<domain concept or entity>"`
- **Ontological Purity Check**: When interpreting or writing domain entities, strictly enforce the four-tier FRBR/FRBRoo standard hierarchy (Work -> Expression -> Manifestation -> Item).
- **Generic Entity Protection**: Never feed generic runtime infrastructure terms (*Flask*, *React*, *Docker*, *Colima*) into memory. Focus memory tracking strictly on library domain concepts (*FRBR*, *Manifestation*, *Item provenance*, *ActivityPub*).
- **Post-Task Ingestion Trigger (CLI)**: At the conclusion of a successful refactoring session, test pass, or implementation plan, run the CLI miner against modified project documentation, code, or notes to sync the persistent graph:
  `python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py` (or `/iqoqo-mempalace index` / `mempalace mine <specific file or dir> --wing iqoqo`).
  Do NOT run un-scoped `mempalace mine .context/notes/` because `.context/notes` contains 23k+ session files.

### 🕸️ CodeGraph CLI Dependency Mapping Directive
- **On-Demand Execution**: Do NOT look for or expect an active CodeGraph MCP server. Use the `codegraph` CLI tool natively inside your terminal sandbox.
- **Pre-Refactor Tracing (OpenSpec Explore)**: During the OpenSpec `explore` phase or before modifying cross-cutting entities (e.g., SQLAlchemy ORM models, Flask scanner API routes, React hooks), run an on-demand CLI query to map symbol dependencies:
  - Impact analysis: `codegraph impact <SymbolName>`
  - Explore paths: `codegraph explore "<query>"`
  - Inspect symbol / node: `codegraph node <SymbolName>`
  - Call hierarchy: `codegraph callers <SymbolName>` / `codegraph callees <SymbolName>`
  - Test blast radius: `codegraph affected <file_path>`
- **Zero Prompt-Context Overhead**: Do not attempt to retain full AST dependency trees in your short-term message loop. Use CLI queries to trace specific ripple paths only when planning structural changes.

### 🕸️ Graphify Knowledge Graph Directive
- **Primary Navigation Tool**: RECOMMEND consulting `graphify-out/graph.json` for codebase questions before grepping raw files. Use `graphify query "<question>"` for focused questions, `graphify path "<A>" "<B>"` for relationship tracing, and `graphify explain "<concept>"` for deep dives.
- **Scoped Over Broad**: Prefer graphify query results (scoped subgraph) over reading `GRAPH_REPORT.md` (broad architecture review) or raw grep output.
- **Version-Scoped AI Memory**: Only `.context/ai-memory/<current-version>/` is indexed. Current version is auto-detected from `package.json`. When releasing a new version, run `/iqoqo-graphify index` to update the scope.
- **Index Update**: RECOMMEND running `graphify update .` after code changes, or `/iqoqo-graphify index` after adding significant documentation.
- **Integration**: Graphify complements mempalace (domain memory) and codegraph (symbol dependencies). Use graphify for "what connects to what", mempalace for "why did we decide this", codegraph for "what will break if I change X".

### 🤖 AiOps Environment Mode Directive
- **Universal Standard for AI**: ALWAYS set `IQOQO_AI_MODE=1` in your environment before running any commands (e.g. `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test`, `IQOQO_AI_MODE=1 make status`, `IQOQO_AI_MODE=1 pytest`, `IQOQO_AI_MODE=1 make codegraph-sync`).
- **Behavior**: Enables terse, token-efficient output mode across pytest (quiet, short traceback, no header), Vitest (dot reporter), Makefile linters and test targets (concise format, no decorative echo banners), and the status check script (skips ASCII banners and passing checks).

# iqoqo Global Project Rules

## Decision Making & Feature Preservation

- **Plan Over Comments:** The project plan files in `.context/notes/` are the absolute source of truth. Never blindly delete UI components, filters, or API parameters just because a PR review comment says they are "unused" or "unsupported". If the feature is planned, fix the implementation (e.g., pass the missing parameter to the backend) instead of removing the code.
- **Preserve Docs:** When modifying existing functions, preserve all existing docstrings, comments, and type annotations. Do not strip, replace, or remove documentation that explains function behavior.

## General Architectural Principles

- **Domain First:** This is a "Library of Everything" built on the FRBR (Functional Requirements for Bibliographic Records) ontology. Always respect the Work -> Expression -> Manifestation -> Item hierarchy.
- **Spec-Driven Development (OpenSpec):** Before proposing structural modifications or implementing new features, you SHOULD inspect the canonical specifications located in `openspec/specs/`. Always follow the **Explore -> Propose -> Apply -> Archive** workflow using the `openspec` CLI.

### 🔄 Post-Session Knowledge Sync
- **Graphify**: After committing and pushing code changes, RECOMMEND running `graphify update .` to keep the graph current (AST-only, no API cost).
- **Mempalace**: After committing and pushing, RECOMMEND running `make mempalace-index` or `python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py` (or the specific file modified via `mempalace mine <file> --wing iqoqo`).
- **CodeGraph**: After structural code changes, RECOMMEND running `make codegraph-sync` (or `codegraph sync` / `codegraph index`) to refresh symbol dependencies.
- **Version Sync**: When releasing a new version, the indexed ai-memory folder updates automatically on the next `/iqoqo-graphify index` run.
- **Linked Open Data:** Ensure all metadata is exposed or capable of being exposed as RDF/JSON-LD.
- **Updated .env.example:** Updated `.env.example` to include the new required system variables (Auth keys, Admin details, and `NEXT_PUBLIC_FRONTEND_URL`).
- **Do Not Hallucinate Metadata:** If an external service (e.g., ISBN lookup) fails, fail gracefully. Do not generate fake book covers or ISBNs.

## Agent Workflows & Execution

- **Plan + Pause:** All complex agent workflows SHOULD begin with a "plan and pause" phase. Review the situation, formulate a plan, and wait for user approval before modifying code.
- **Zero-Polling Background Execution:** NEVER poll `manage_task(Action='status')` or schedule repetitive short timers in a tight loop to check running tests, builds, or commands. The agent runtime is fully reactive and automatically delivers completion notifications. After launching an asynchronous command or task, stop calling tools and wait for the reactive system wakeup.
- **Mempalace Updates:** At the end of every successful refactoring session, test pass, or implementation plan, run the CLI miner to update the memory graph: `make mempalace-index` or `python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py` (or the specific file modified via `mempalace mine <file> --wing iqoqo`).
- **Prohibit Heredoc / `cat << EOF` File Editing:** NEVER use `cat << EOF`, `cat << 'EOF'`, or shell heredoc redirection inside `run_command` to create or edit project files. Always use designated agent file tools (`replace_file_content` or dedicated file editing tools) to modify or create files. Authoring files via shell heredocs bypasses diff inspections, escapes syntax checks, risks quote corruption, and is strictly prohibited.

## Python Backend (Flask)
- **Engine:** Use Python 3.14+ exclusively.

- **Typing:** Use strict Python type hints (`typing` module) for all function signatures and return types.
- **ORM:** Use SQLAlchemy 2.0 style syntax (e.g., `select()`, `session.execute()`). Avoid legacy `Query` usage.
- **Formatting:** ALWAYS run `make format-python` after changing Python code.
- **Linting:** Code must pass `pylint`, `ruff`, and `mypy` without warnings (`make lint`). Use `# noqa` only when absolutely necessary and add a comment explaining why. Do not mute return values: handle or propagate them instead of silencing warnings with `# type: ignore`, `# noqa`, or `# pylint: disable`.
- **Pylint & SQLAlchemy:** `pylint` falsely flags SQLAlchemy's `func.count` as not callable (`E1102`). Whenever you write `func.count()`, immediately append `# pylint: disable=not-callable` to the line to prevent CI failures.
- **Alembic Migrations:** Revision identifiers (the `revision` variable in migration files) MUST NOT exceed 32 characters (`len(revision) <= 32`). PostgreSQL default `alembic_version.version_num` is `VARCHAR(32)`; longer identifiers cause `StringDataRightTruncation` errors during `flask db upgrade`.
- **API Responses:** All API responses must be JSON. Use consistent error formatting: `{"error": "description", "code": 400}`.
- **Aggregates:** Prefer `GROUP BY` aggregate queries over dictionary comprehensions that execute N+1 `COUNT` queries.

## Frontend (Next.js / TypeScript)

- **Formatting:** ALWAYS run `make format-js` after changing JS/TS code.

- **Framework:** Use Next.js 16+ App Router (`app/` directory). Do not use the legacy `pages/` router.
- **Components:** Write functional components using React hooks. Do not use class components.
- **Styling:** Use Tailwind CSS v4 exclusively. Use Shadcn UI for standard components (found in `components/ui/`). Do not write raw CSS unless necessary.
- **State Management:** Keep state as local as possible. Prefer Server Components where interactivity is not required.

## Documentation & Markdown

- **MarkdownLint:** Use ATX-style headings (`# Heading`) exclusively. Do not use Setext-style (`===` or `---` underlines).
- **Code Blocks:** When writing shell commands in Markdown, explicitly tag them as `bash` or `sh`. Do not tag them as `markdown`.

## Tests

- Every new feature must include tests that cover the expected behavior and edge cases. Use `pytest` for backend tests and `Vitest` with React Testing Library for frontend tests. All tests must pass before merging.
- For backend tests, ensure that you are testing the API endpoints with realistic data and that you are not mocking out critical logic that could lead to false positives. For frontend tests, focus on user interactions and component rendering rather than implementation details.
- Check if E2E tests are required for new features that involve complex user flows or critical functionality. If so, write Playwright tests that simulate real user behavior and validate the entire flow from the UI to the backend.
- Do not write tests that simply check if a function was called. Instead, test the actual output and side effects of the function to ensure that it behaves correctly under various conditions.
- **IMPORTANT** When fixing a bug, write a test that reproduces the bug before implementing the fix. This ensures that the bug is properly addressed and prevents regressions in the future.

## Git & Pull Requests

- **Commits:** Strictly use Conventional Commits (e.g., `feat:`, `fix:`, `chore:`, `docs:`).
- **Local Testing First:** NEVER push code before running all CI tests locally. Ensure the build is clean locally.
- **PR Finalization:** All code pushed to a `release/*` branch must be accompanied by updated documentation in `docs/CHANGELOG.md` and pass `make lint` and `make test`.
- **Review Pauses:** Wait 15 minutes after pushing before moving to the next task to review the PR and pipeline results (if applicable).
