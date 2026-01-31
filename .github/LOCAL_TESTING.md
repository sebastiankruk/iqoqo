# Running GitHub CI Tests Locally

Before pushing to GitHub, you can run all the same tests that GitHub Actions will run.

## Prerequisites

Make sure you have installed all dependencies:

```bash
pip install -r requirements.txt
npm install
```

## Quick Test Commands

### Run ALL Tests (Same as GitHub)

```bash
make lint    # Run all linting
make test    # Run all pytest tests
```

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

## GitHub Actions Workflow

The `.github/workflows/quality.yml` runs:

1. **lint-python** - Ruff, Black, isort, and mypy (NOT pylint)
2. **lint-javascript** - ESLint, Prettier, and Stylelint
3. **lint-markdown** - markdownlint-cli2
4. **test** - Full pytest suite

**Note:** The local test `test_pylint_linting` may fail due to virtual environment detection issues, but this is NOT run in GitHub CI. You can skip it with:

```bash
pytest tests/ -k "not test_pylint_linting"
```

## Tips

- Run `make lint-css` and `make lint-js` before every commit (these match GitHub exactly)
- Use `ruff check app/ tests/ scripts/` - this is what GitHub uses
- Use `make format` to auto-format Python code
- Most important: ruff, mypy, pytest, and stylelint must pass cleanly
- To run the exact same tests as GitHub CI:

  ```bash
  # Python linting (what GitHub runs)
  ruff check app/ tests/ scripts/
  black --check app/ tests/ scripts/
  isort --check-only app/ tests/ scripts/
  mypy app/ tests/

  # JS/CSS linting (what GitHub runs)
  npx eslint "app/web/static/js/**/*.js"
  npx stylelint "app/web/static/css/**/*.css"

  # Tests (what GitHub runs)
  pytest tests/ -v
  ```
