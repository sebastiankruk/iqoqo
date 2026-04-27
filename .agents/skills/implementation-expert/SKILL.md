---
name: implementation-expert
description: "Expert skill for implementing features from code snippets OR generating plans from product improvements when code is missing."
license: AGPL
compatibility: [opencode, antigravity]
metadata: { audience: developers }
---

# Skill: Implementation Expert

This skill governs codebase changes. It handles provided code OR generates required code from high-level goals.

## Core Rules

1. **Source of Truth**: `.context/private-notes/` is law. Plan files there override all.
2. **Mirror Patterns**: Match existing style, imports, and logic exactly. No "improvements" unless asked.
3. **Type Safety**: No `# type: ignore` unless for SQLAlchemy dynamic attrs or broken external stubs. Fix the code.
4. **Environment**: Use `.venv/bin/` for all Python tools (pytest, flask, alembic).
5. **Copyright**: Every new file (.py, .ts, .tsx) MUST have the standard iqoqo AGPL header.
6. **FRBR Hierarchy**: Respect Work -> Expression -> Manifestation -> Item ontology.

## Implementation Workflow

### Phase 1: Planning (If no code provided)
- **Explore**: Search `app/api/`, `app/core/`, `app/db/`, and `frontend/components/` for similar patterns.
- **Draft**: Create incremental snippets (patches) matching explored patterns.
- **Markers**: Use `Add to {path} after {context}:` to define insertion points.

### Phase 2: Execution
- **Apply**: Use `replace_file_content` or `multi_replace_file_content` for snippets or full files.
- **QA**: Run `make lint` and `make test`. If fail, fix code until green.
- **Cleanup**: Auto-fix lints with `ruff check --fix` or `black` without changing logic.
- **Git**: Conclude with `git add` and `git commit` using Conventional Commits.

## Copyright Header
```python
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
```

Base directory for this skill: `.agents/skills/implementation-expert`
Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory.
