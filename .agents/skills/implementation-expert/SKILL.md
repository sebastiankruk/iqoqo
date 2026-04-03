# Skill: Implementation Expert

This skill defines the protocol for implementing features in the iqoqo repository when pre-written code snippets, text, or diffs are provided by the USER.

## Core Directives

1. **Source of Truth**: Always check `.github/context/private-notes/code/` for the latest implementation specifics. If a file or diff is found there, it takes absolute precedence over any other documentation or hallucinate-able logic.
1. **Strict Adherence**: Copy provided code exactly as provided. Do not "improve" or "clean up" the provided snippets unless explicitly asked to do so.
1. **Environment Parity**: Always execute Python commands (flask, pytest, etc.) using the project's virtual environment: `.venv/bin/`.
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
    # along with this program.  If not, see <https://www.gnu.org/licenses/>
    #
    ```

## Implementation Workflow

1. **Read and Parse**: Carefully read the provided markdown file or prompt containing the code.
1. **Validate**: Verify the target file paths exist in the current workspace.
1. **Apply**: Use `replace_file_content` or `multi_replace_file_content` to apply the changes exactly specified.
1. **Enforce QA**: Never conclude a task without running `make lint` and `make test`.
1. **Clean Lints**: If the provided code triggers lint warnings (e.g., import sorting), fix them using `ruff check --fix` or `black` before final submission, but DO NOT alter the core logic.
