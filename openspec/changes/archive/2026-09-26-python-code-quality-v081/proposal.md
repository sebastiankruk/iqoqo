## Why

The iqoqo codebase has accumulated pylint warnings that violate the project's own lint safeguard tests (`test_no_too_many_return_statements_disables`, `test_no_broad_exception_caught_disables`). These tests enforce clean refactoring over suppression, but the underlying code issues remain unfixed. With v0.8.1 approaching, resolving these warnings ensures the codebase meets its own quality standards, reduces maintenance burden, and prevents the safeguard tests from becoming dead code.

## What Changes

- **Module decomposition**: Split `app/api/public.py` (1033 lines) into `public_profile.py`, `public_items.py`, `public_rdf.py`; split `scripts/etl_frbr_safe.py` (1534 lines) into `etl/reconcile.py`, `etl/backup.py`, `etl/merge.py`
- **Strategy pattern refactoring**: Replace the 13-return `classify_operation()` in `app/api/sparql.py` with dictionary dispatch
- **Specific exception handling**: Replace 27 `broad-exception-caught` occurrences across `app/core/sparql_service.py`, `app/api/sparql.py`, tests, and scripts with specific exception types (`ValueError`, `TypeError`, `KeyError`, `OSError`, `subprocess.SubprocessError`)
- **Context manager adoption**: Wrap `_query_semaphore.acquire()`, `_MP_CONTEXT.Pipe()`, and `_MP_CONTEXT.Process()` in `app/core/sparql_service.py` with proper `with` statements or try/finally blocks
- **Type safety fix**: Resolve `unsubscriptable-object` warning in `tests/test_etl_frbr_safe.py:412`
- **Backward compatibility**: All existing imports and public APIs remain functional through re-exports

## Capabilities

### New Capabilities

_None — this is a pure code quality refactoring with no spec-level behavior changes._

### Modified Capabilities

_None — no existing capability requirements are changing._

> **Note**: `skip_specs: true` is set in `.openspec.yaml` because this change involves only internal code structure improvements (module splitting, pattern refactoring, exception specificity) without altering any external behavior, API contracts, or user-facing features.

## Impact

- **Code**: `app/api/public.py`, `app/api/sparql.py`, `app/core/sparql_service.py`, `scripts/etl_frbr_safe.py`, `tests/test_etl_frbr_safe.py`, `tests/test_sparql_*.py`, `tests/test_public_rdf_safety.py`
- **APIs**: No breaking changes — all existing routes and functions remain accessible via re-exports from original module paths
- **Dependencies**: No new dependencies required
- **Systems**: CI/CD pipeline will see pylint score improve to 10.00/10; lint safeguard tests will pass with actual code fixes rather than relying on the absence of violations
- **Testing**: All existing tests must continue to pass; no new test files required (existing test suites provide coverage)
