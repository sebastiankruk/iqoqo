## 1. Pytest AI Mode (conftest.py Hook)

- [x] 1.1 Add a `pytest_configure(config)` hook at the top of `tests/conftest.py` that checks `os.environ.get("IQOQO_AI_MODE")`. When set, override `config.option` to apply `-q --tb=short --no-header` and disable verbose plugins (e.g., `-p no:sugar`). Verify by running `IQOQO_AI_MODE=1 .venv/bin/pytest tests/ -x --co` and confirming reduced output vs running without the env var.
- [x] 1.2 Add a test in `tests/test_aiops_mode.py` that imports the `pytest_configure` hook and asserts it modifies `config.option.verbose` and `config.option.tbstyle` when `IQOQO_AI_MODE` is set. Verify by running `pytest tests/test_aiops_mode.py`.

## 2. Vitest AI Mode (Config Detection)

- [x] 2.1 Update `frontend/vitest.config.ts` to check `process.env.IQOQO_AI_MODE` and conditionally set `reporter: 'dot'` when truthy, keeping the current default otherwise. Verify by running `IQOQO_AI_MODE=1 npx vitest run` and confirming dot-style output vs normal verbose output without the env var.

## 3. Makefile Lint Terse Mode

- [x] 3.1 Update `Makefile` lint targets (`lint-python`, `lint-format`, `lint-js`, `lint-css`, `lint-markdown`) to use `ifdef IQOQO_AI_MODE` guards that: (a) suppress decorative `@echo "Running X..."` banners, (b) pass `--output-format=concise` to ruff, (c) pass compact message template to pylint, and (d) pass `--no-error-summary` to mypy. Verify by running `IQOQO_AI_MODE=1 make lint-python` and comparing output size to `make lint-python`.
- [x] 3.2 Update `Makefile` test targets (`test-backend`, `test-frontend`, `test-scripts-bash`, `test-scripts-python`) to suppress decorative echo banners when `IQOQO_AI_MODE` is set. The actual tool flags are handled by conftest.py/vitest.config.ts, so only the echo suppression is needed here. Verify by running `IQOQO_AI_MODE=1 make test-backend`.

## 4. Status Script AI Mode

- [x] 4.1 Update `scripts/iqoqo-status.sh` to check for `IQOQO_AI_MODE`. When set, bypass printing the ASCII banner and headers, and inside the `check()` function, quietly return for `pass` or `info` statuses. Verify by running `IQOQO_AI_MODE=1 make status` and ensuring only failures/warnings (or nothing if all healthy) and the final summary are printed.

## 5. Automated Regression Testing (Scripts)

- [x] 5.1 Update `tests/bash/iqoqo_status.bats` to add a test case verifying that running `IQOQO_AI_MODE=1 scripts/iqoqo-status.sh` suppresses ASCII banners and successfully returns (mocking necessary internal conditions if needed).
- [x] 5.2 Update `tests/bash/makefile_tooling.bats` (or a similar test file) to add a test case asserting that `make lint` or `make test` correctly swallows the `@echo` commands when `IQOQO_AI_MODE=1` is exported in the environment.

## 6. Documentation & Agent Rules

- [x] 6.1 Add `IQOQO_AI_MODE=` entry to `.env.example` with a comment explaining it enables terse output for AI agents.
- [x] 6.2 Edit `.agent/rules/iqoqo-standards.md` to add a new top-level directive `### 🤖 AiOps Environment Mode` that explains the `IQOQO_AI_MODE=1` variable and instructs the agent to set it before running tests, lints, or status commands.

## 7. End-to-End Verification

- [x] 7.1 Run `IQOQO_AI_MODE=1 make test-backend` and confirm it produces significantly shorter output.
- [x] 7.2 Run `.venv/bin/pytest tests/test_feedback_tickets.py` directly with `IQOQO_AI_MODE=1` and confirm terse output is applied.
- [x] 7.3 Run `IQOQO_AI_MODE=1 make status` and confirm it skips decorative UI elements and passed checks.
- [x] 7.4 Run `make test-scripts-bash` to confirm the new Bats regressions tests pass.
