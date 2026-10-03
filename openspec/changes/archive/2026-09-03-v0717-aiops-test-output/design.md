## Context

See `proposal.md` for the motivation. AI agents interact with the iqoqo toolchain in multiple ways:

1. **Via Makefile** — `make test`, `make lint`, `make test-backend`, etc.
2. **Direct invocation** — `pytest tests/test_foo.py`, `npx vitest run`, `.venv/bin/ruff check app/foo.py`
3. **Sub-commands** — Agents may run individual test files or lint a single module

A make-target-only solution (`make test-ai`) would miss paths 2 and 3 entirely.

## Goals / Non-Goals

**Goals:**
- Single environment variable `IQOQO_AI_MODE=1` that globally switches all test/lint output to terse mode.
- Works whether tools are invoked via `make`, direct CLI calls, or programmatic invocation.
- Affects: pytest, vitest, ruff, pylint, mypy, black, eslint, stylelint, markdownlint.
- Short tracebacks on failures preserved (AI still needs error context).

**Non-Goals:**
- Changing test logic or assertions.
- Changing default output for human developers (when `IQOQO_AI_MODE` is unset, everything behaves as today).
- Custom AI reporter implementations (use existing terse reporters built into each tool).

## Decisions

### 1. Env Var Name: `IQOQO_AI_MODE`

Project-namespaced to avoid collisions. Simple truthy check (`1`, `true`, `yes` all work).

### 2. Pytest: conftest.py Early Hook

Add a `pytest_configure` hook in `tests/conftest.py` that checks `os.environ.get("IQOQO_AI_MODE")`:
- Override `addopts` to `-q --tb=short --no-header -p no:sugar -p no:verbose`
- Suppress plugin banners and progress bars
- This fires for ALL pytest invocations (make, direct, single-file) because conftest.py is auto-loaded

### 3. Vitest: Config-Level Detection

In `frontend/vitest.config.ts`, check `process.env.IQOQO_AI_MODE`:
- If set: use `reporter: 'dot'` and disable watch mode
- If unset: keep current default behavior
- This fires for all vitest invocations (make, direct npx, npm script)

### 4. Makefile: Conditional Echo + Linter Flags

Use `ifdef IQOQO_AI_MODE` guards in Makefile:
- Suppress decorative `@echo "Running ruff..."` banners
- Pass `--output-format=concise` to ruff (instead of default full)
- Pass `--msg-template='{path}:{line}: {msg} ({symbol})'` to pylint for single-line output
- Pass `--no-error-summary` to mypy (errors are enough, no recap needed)

### 5. Agent Rules Update

Add guidance to `.agent/rules/iqoqo-standards.md` recommending agents set `IQOQO_AI_MODE=1` before running any test, lint, or status commands. It should be added as a top-level directive.

### 6. Status Script Terse Mode

In `scripts/iqoqo-status.sh`, check for `IQOQO_AI_MODE`:
- If set, suppress all `pass` and `info` checks.
- Only output `warn` and `fail` checks, along with the final error/warning count summary.
- Strip all decorative ASCII art and headers to keep tokens to an absolute minimum.

### 7. Automated Regression Testing

To prevent regressions in our tooling, we will update the existing Bats test suite (`tests/bash/iqoqo_status.bats` and `tests/bash/makefile_tooling.bats`) to explicitly assert that standard mode remains verbose, and AI mode strips the expected banners, headers, and noisy output.

## Risks / Trade-offs

- **Risk:** Agents may not know to set the env var.
  **Mitigation:** Document in agent rules (`iqoqo-standards.md`) AND in `.env.example`. Future agent skills can also auto-set it.

- **Risk:** Too-terse output may hide context on failures.
  **Mitigation:** `--tb=short` still shows traceback + assertion; only progress/header/banner noise is removed. `make status` will still print all warnings and failures.
