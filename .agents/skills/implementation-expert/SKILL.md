---
name: implementation-expert
description: "Skill for implementing features in the iqoqo repository when pre-written code snippets, text, or diffs are provided by the user."
license: AGPL
compatibility:
  - opencode
  - antigravity
metadata:
  audience: developers
---
# Skill: Implementation Expert

This skill defines the protocol for implementing features in the iqoqo repository when pre-written code snippets, text, or diffs are provided by the USER.

## Tech Stack Context
- **Backend**: Python Flask, PostgreSQL, Pytest, Ruff/Black, Alembic, FRBR-based ontology mapping.
- **Frontend**: React, Next.js, TypeScript, Vitest, ESLint.
- **Orchestration**: `make lint`, `make test`.

## Core Directives

1. **Source of Truth**: Always check `.github/context/private-notes/code/` for the latest implementation specifics. If a file or diff is found there, it takes absolute precedence over any other documentation.
1. **Strict Adherence**: Copy provided code exactly as provided. Do not "improve" or "clean up" the provided snippets unless explicitly asked to do so.
1. **No Architectural Changes & No Feature Creep**: Do not alter the architecture, tech stack, or overarching design. ONLY fix or implement the code exactly as requested. Do not add unrelated features.
1. **Preserve Existing Code**: Do not delete or refactor existing code unless the plan explicitly instructs you to do so.
1. **Completeness**: Ensure all specified tests, documentation updates (in `docs/`), and database migrations (Alembic) mentioned in the plan are fully implemented.
1. **Environment Parity**: Always execute Python commands (flask, pytest, alembic, etc.) using the project's virtual environment: `.venv/bin/`.
1. **Copyright Compliance**: Every new source file (.py, .ts, .tsx) MUST include the standard iqoqo copyright header:

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
    # along with this program.  If not, see [https://www.gnu.org/licenses/](https://www.gnu.org/licenses/)
    #
    ```

## Implementation Workflow

1. **Read and Parse**: Carefully read the provided markdown plan, prompt, or diff containing the code.
1. **Validate**: Verify the target file paths exist in the current workspace. Provide necessary shell commands to create/move files if applicable.
1. **Apply**: Use `replace_file_content` or `multi_replace_file_content` to apply the changes exactly as specified.
1. **Enforce QA**: Never conclude a task without running `make lint` and `make test`. Ensure no tests are failing.
1. **Analyze Failures**: If tests or linters fail, introduce code modifications strictly needed to make them pass. Do not rewrite the whole file unless necessary.
1. **Clean Lints**: If the provided code triggers lint warnings (e.g., import sorting), fix them using `ruff check --fix` or `black` before final submission, but DO NOT alter the core logic.
1. **Git Workflow**: Conclude the implementation by providing the necessary `git add` and `git commit` commands with a concise, descriptive commit message once all QA passes.
