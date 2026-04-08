---
description: "Skill for intelligently running lint and test suites using Makefile sub-tasks to save time."
---
# Smart Makefile Tester

## Context
You must optimize the feedback loop to save time and tokens. Prevent trivial linting failures by formatting first. Project iqoqo uses a Makefile for testing and linting. Full runs (`make lint`, `make test`) can be time-consuming. You must optimize the feedback loop.

## Instructions

1. **Pre-emptive Formatting:** BEFORE running any linters, ALWAYS run code formatters to fix trivial issues automatically using the virtual environment:
   - Run: `.venv/bin/python -m black app/ tests/ scripts/` (or `.venv/bin/python -m make format-python`)
   - Ensure your Markdown edits does not violate Rules like MD003 (Heading style)
1. **Testing:** Run `make test` (or ensure it uses `.venv/bin/pytest`).
   - *Known Issue:* You will see `ECONNREFUSED ::1:3000` AggregateErrors during frontend tests. Ignore these; they are expected when the Next.js dev server is not running. As long as the final test exit code is `0`, tests passed.
1. **Initial Run:** Execute the master command using the virtual environment if applicable (`.venv/bin/python -m make lint` or `.venv/bin/python -m make test`).
1. **Identify Failures:** If the master command fails, identify which specific sub-task failed (e.g., `flake8`, `mypy`, `pytest` for backend, or `npm run lint`, `vitest` for frontend). Always run backend sub-tasks via `.venv/bin/python -m <tool>`.
1. **Targeted Re-runs:** Fix the underlying code issue. Do **not** run the master command again yet. Instead, run the specific failing sub-task command directly to verify the fix quickly. Always prioritize `.venv/bin/` paths for Python tools:
   - Example: `.venv/bin/pytest tests/test_api.py -k test_name`
   - Example: `.venv/bin/python -m ruff check app/`


- lint           - Run all linting checks
- lint-python    - Run Python linters (ruff, mypy, pylint)
- lint-format    - Check Python code formatting (black)
- lint-js        - Run legacy JavaScript linter (eslint)
- lint-frontend  - Run Next.js / TypeScript linter
- lint-css       - Run CSS linter (stylelint)
- lint-markdown  - Run Markdown linter
- format         - Format all code
- format-python  - Format Python code (black, isort)
- format-js      - Format JavaScript code (prettier)
- test           - Run all tests (backend and frontend)
- test-backend   - Run backend tests (pytest)
- test-frontend  - Run frontend tests (Vitest)
- build-frontend - Build Next.js production bundle
- clean          - Remove build artifacts

1. **Final Verification:** Once the targeted sub-task passes, run the master command (`make lint` or `make test`) one final time to ensure no other areas were broken by your fix.
