---
description: Load iqoqo project-specific instructions and personas
---

1. **Read Core Directives**: Always check [.github/copilot-instructions.md](.github/copilot-instructions.md) for current FRBR architecture and tech stack requirements.
2. **Follow Modeling Rules**: Apply the Work → Expression → Manifestation → Item hierarchy globally.
3. **Check Private Notes**: List and read relevant files in [.context/notes/](file:///.context/notes/) (including `plan/`, `bugs/`, etc.) to find detailed implementation requirements.
4. **Assume Persona**:
   - Default: Senior full-stack architect.
   - On request: Switch to the precise mode in [.github/agents/junior-dev.agent.md](.github/agents/junior-dev.agent.md).
5. **Enforce QA**: Never conclude a task without running `make lint` and `make test`.
6. **Knowledge Tools First**: Before grep/find, use the knowledge indexing tools:
   - **CodeGraph** (`codegraph node/impact/callers/affected`): Symbol-level code intelligence, blast radius, call hierarchy
   - **Graphify** (`graphify query/explain/path`): Natural language exploration, shortest paths, community detection
   - **mykg** (MCP tools: `search_nodes`, `get_node`, `get_neighbors`): Domain ontology entities (Work, Expression, Manifestation, Item)
   - **MemPalace** (`mempalace search "<keywords>" --wing iqoqo`): Conversation history, architectural decisions, past bugs
7. **Review Workflow**: For code reviews, load the `code-reviewer` skill which integrates all four knowledge tools.
