# Running GitHub CI Tests Locally

Before pushing to GitHub, you can run all the same tests that GitHub Actions will run.

## Prerequisites

Make sure you have installed all dependencies:

```bash
pip install -r requirements.txt
npm install
```

## Quick Test Commands

### Run Canonical GitHub Quality Checks

```bash
IQOQO_AI_MODE=1 make lint # Run the effective quality.yml lint checks
make test    # Run all pytest tests
```

`make lint` is the compatibility baseline for the executable lint steps in
`.github/workflows/quality.yml`. It gates Ruff, Black, isort, Markdownlint, and
license checks. Mypy runs with the workflow's `continue-on-error: true`
semantics: its failure diagnostics are retained, but it does not fail
`make lint`. The JavaScript quality job installs ESLint, Prettier, and Stylelint
but does not execute any of them; the separate frontend test job does run
TypeScript `type-check`, but it is not part of the lint jobs.

`make lint-all` additionally runs local-only Pylint, ESLint, TypeScript,
Stylelint, and YAML validation checks. These stricter checks are intentionally
not CI compatibility gates.

### Individual Test Categories

#### 1. Python Linting

```bash
make lint-python      # Ruff + mypy + pylint
make lint-format      # Black + isort
```

#### 2. JavaScript/CSS Linting

```bash
make lint-js          # ESLint
make lint-css         # Stylelint
```

#### 3. Python Tests

```bash
make test
# or more verbose:
pytest tests/ -v
```

#### 4. Specific Test Files

```bash
pytest tests/test_api.py -v
pytest tests/test_migration.py -v
```

## Common Issues Fixed

### Issue 1: CSS Stylelint Errors

**Error:** `Unexpected unknown value "none" for property "margin"`
**Fix:** Change `margin: none` and `padding: none` to `margin: 0` and `padding: 0`

### Issue 2: Module Import Errors in Tests

**Error:** `ModuleNotFoundError: No module named 'scripts'`
**Fix:** Add `sys.path` manipulation in test files that need to import from scripts:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.sql_to_json import parse_sql_dump
```

### Issue 3: Duplicate Exception Handlers

**Error:** `B025 try-except block with duplicate exception`
**Fix:** Remove duplicate exception handlers in your code

## Tips

- Run `make lint` for the GitHub lint baseline; use `make lint-all` for stricter local diagnostics.
- Use `ruff check app/ tests/ scripts/` - this is what GitHub uses
- Use `make format` to auto-format Python code
- Mypy diagnostics are advisory in the existing workflow; Ruff, Black, isort, Markdownlint, and license checks gate it.
- To run the exact same tests as GitHub CI:

  ```bash
  # Python linting (what GitHub runs)
  ruff check app/ tests/ scripts/
  black --check app/ tests/ scripts/
  isort --check-only app/ tests/ scripts/
  mypy app/ tests/ scripts/ # advisory only: workflow continue-on-error

  # Tests (what GitHub runs)
  pytest tests/ -v
  ```
