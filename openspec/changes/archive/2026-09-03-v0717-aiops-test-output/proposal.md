## Why

Current test and lint outputs include verbose progress bars, detailed docstrings, and non-essential logging that significantly consume token budgets when evaluated by automated LLM review harnesses. AI coding agents (Antigravity, Copilot, Cursor, etc.) invoke tools both through `make` targets AND by calling `pytest`, `vitest`, `ruff`, `pylint`, `mypy` directly. Adding new `make test-ai` targets would only cover the `make` path — direct tool invocations would remain verbose.

An environment-variable-driven approach (`IQOQO_AI_MODE=1`) ensures **every** tool invocation automatically switches to terse, token-efficient output regardless of how it's called.

## What Changes

- Introduce `IQOQO_AI_MODE` environment variable as the single control flag.
- Update `pyproject.toml` `[tool.pytest.ini_options]` to conditionally apply terse flags (`-q --tb=short --no-header`) when `IQOQO_AI_MODE` is set, via a `conftest.py` hook.
- Update `frontend/vitest.config.ts` to detect `process.env.IQOQO_AI_MODE` and switch reporter to `dot` or `basic`.
- Update `Makefile` lint targets to suppress decorative echo banners and reduce ruff/pylint/mypy verbosity when `IQOQO_AI_MODE` is set.
- Update `tests/conftest.py` to install a pytest plugin that modifies `addopts` at startup when the env var is detected.
- Document the env var in `.env.example` and `README.md`.

## Capabilities

### New Capabilities

- None (infrastructure/DX change only)

### Modified Capabilities

- None (`.openspec.yaml` has `skip_specs: true`)

## Impact

- `tests/conftest.py`: Modified to detect `IQOQO_AI_MODE` and override pytest verbosity at startup.
- `frontend/vitest.config.ts`: Modified to conditionally set terse reporter.
- `Makefile`: Modified to conditionally suppress echo banners and pass terse flags to linters.
- `pyproject.toml`: Optionally add an `[tool.pytest.ini_options]` marker for documentation.
- `.env.example`: Updated with `IQOQO_AI_MODE` documentation.
- Agent rule files (`.agent/rules/`): Updated to recommend agents set `IQOQO_AI_MODE=1` before running tests/lints.
