---
name: makefile-tester
description: "Skill for intelligently running lint and test suites using Makefile sub-tasks to save time."
license: AGPL
compatibility:
  - opencode
  - antigravity
metadata:
  audience: testers
---
# Smart Makefile Tester

## Context

You must optimize the feedback loop to save time and tokens. Prevent trivial linting failures by formatting first. Project iqoqo uses a Makefile for testing and linting. Full runs (`make lint`, `make test`) can be time-consuming. You must optimize the feedback loop.

### Verified Binary Paths

- **Python Venv:** `.venv/bin/python` (use with `-m pytest`, `-m ruff`, etc.)
- **Node/NPM/NPX:** `/Users/sebastiankruk/.nvm/versions/node/v20.10.0/bin`
  - Prepend this to `PATH` before running `npx` or `npm` commands.

## Instructions

1. **Pre-emptive Formatting:** BEFORE running any linters, ALWAYS run code formatters to fix trivial issues automatically:
   - **Python:** `.venv/bin/black app/ tests/ scripts/` and `.venv/bin/isort app/ tests/ scripts/` (or run `make format-python`)
   - **Frontend (TS/JS/CSS):** Prepend Node path and run `cd frontend && npx prettier --write "**/*.{ts,tsx,css}" --ignore-path .gitignore` (or run `make format-js`)
   - Ensure your Markdown edits do not violate Rules like MD003 (Heading style).

2. **Run Master Lints/Tests:** Or run individual sub-tasks to verify changes rapidly.

3. **Sub-Task Lint Command Reference:**
   - **Python Ruff Linter:**
     - Command: `.venv/bin/ruff check app/ tests/ scripts/`
     - Makefile: `make lint-python` (also runs mypy and pylint)
   - **Python Mypy Linter:**
     - Command (Local): `.venv/bin/mypy app/ tests/`
     - Command (CI/Quality workflow): `.venv/bin/mypy app/ tests/ scripts/` (runs with `continue-on-error: true`)
   - **Python Pylint:**
     - Command: `.venv/bin/pylint app/ tests/ scripts/`
   - **Python Formatting Checks:**
     - Command: `.venv/bin/black --check app/ tests/ scripts/` and `.venv/bin/isort --check-only app/ tests/ scripts/` (or `make lint-format`)
   - **License Header Check:**
     - Command: `./scripts/check_license.sh` (or `make lint-license`)
   - **Frontend ESLint:**
     - Command: `cd frontend && npm run lint` (or `make lint-js`)
   - **Frontend TypeScript Checks:**
     - Command: `cd frontend && npx tsc --noEmit` (or `make lint-ts`)
   - **CSS Stylelint:**
     - Command: `npx stylelint --allow-empty-input "frontend/app/**/*.css" "frontend/components/**/*.css"` (or `make lint-css`)
   - **Markdown Linter:**
     - Command: `npx markdownlint-cli2 "**/*.md" "#node_modules" "#.venv" "#frontend/node_modules" "#frontend/.next" "#.github" "#.pytest_cache" "#.agents" "#frontend/playwright-report" "#frontend/test-results"` (or `make lint-markdown`)
     - *Note:* CI uses exclude syntax `!node_modules` instead of `#node_modules`.
   - **Verify Permissions:**
     - Command: `.venv/bin/python scripts/sync_permissions.py --verify` (or `make verify-perms`)
   - **Sync Permissions:**
     - Command: `PYTHONPATH=. .venv/bin/python scripts/sync_permissions.py` and `PYTHONPATH=. .venv/bin/python scripts/init_auth.py` (or `make sync-permissions`)

4. **Sub-Task Test Command Reference:**
   - **Backend Tests (pytest):**
     - Command: `.venv/bin/pytest tests/` (or `make test-backend`)
     - CI uses `DATABASE_URL` (e.g. Postgres) and `ADMIN_PASSWORD` environment variables.
   - **Frontend Unit Tests (Vitest):**
     - Command: `cd frontend && npm run test` (or `make test-frontend`)
     - *Known Issue:* You will see `ECONNREFUSED ::1:3000` AggregateErrors during frontend tests. Ignore these; they are expected when the Next.js dev server is not running. As long as the final test exit code is `0`, tests passed.
   - **E2E Tests (Playwright):**
     - Command: `cd frontend && npx playwright test` (or `make test-e2e`)
     - *Local E2E Requirements:* Make sure the DB is initialized and seeded. You can skip reset using `export NO_RESET=1`.
     - *E2E DB Initialization Commands (CI flow):*
       1. (For Postgres) Create schemas: `CREATE SCHEMA IF NOT EXISTS catalog; CREATE SCHEMA IF NOT EXISTS inventory; CREATE SCHEMA IF NOT EXISTS auth;`
       2. Reset database and load seed data: `.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json --reset`
       3. Initialize auth: `ADMIN_PASSWORD=admin PYTHONPATH=. .venv/bin/python scripts/init_auth.py`
       4. Seed E2E data: `PYTHONPATH=. .venv/bin/python tests/e2e/scripts/seed_e2e.py`
     - *E2E Execution Env Vars:*
       `CI=true`, `FLASK_API_URL=http://127.0.0.1:5000/api`, `ADMIN_PASSWORD=admin`, `SECRET_KEY=test-secret-key`

5. **Targeted Re-runs:** Fix the underlying code issue. Do **not** run the master command again yet. Instead, run the specific failing sub-task command directly to verify the fix quickly. Always prioritize `.venv/bin/` paths for Python tools.

6. **Final Verification:** Once the targeted sub-task passes, run the master command (`make lint` or `make test`) one final time to ensure no other areas were broken by your fix.
