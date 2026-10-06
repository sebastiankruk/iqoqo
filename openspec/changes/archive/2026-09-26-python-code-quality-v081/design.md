## Context

The iqoqo Python codebase has lint safeguard tests that prevent muting pylint warnings via inline disables. The codebase currently violates these safeguards with 27+ `broad-exception-caught` occurrences, 13-return functions, oversized modules (>1000 lines), and missing context managers. See proposal.md for the full inventory.

Constraints:
- All existing public APIs must remain importable from their current paths (backward compatibility)
- No new third-party dependencies
- Tests must pass without modification to test expectations (only test *implementation* may change where tests themselves have lint issues)
- The `app/api/public.py` module is imported by Flask blueprints — route registration must be preserved

## Goals / Non-Goals

**Goals:**
- Achieve pylint 10.00/10 on all affected files
- Maintain 100% backward compatibility for all public imports
- Preserve all existing test behavior and assertions
- Keep module cohesion high — each extracted module should have a clear single responsibility

**Non-Goals:**
- Rewriting business logic or changing API behavior
- Adding new features or endpoints
- Refactoring unrelated code (e.g., frontend, non-Python components)
- Changing the lint safeguard tests themselves

## Decisions

### D1: Module extraction via re-export shims

**Decision**: Split `app/api/public.py` into `public_profile.py`, `public_items.py`, `public_rdf.py`, and keep `public.py` as a thin re-export shim that imports and re-exposes all public names.

**Rationale**: Flask blueprint registration and external imports reference `app.api.public`. A re-export shim ensures zero breakage while moving code to focused modules. This is the standard Python pattern for large module decomposition.

**Alternative considered**: Updating all import sites across the codebase. Rejected because it creates a large blast radius and risks missing an import, whereas re-exports are guaranteed to work.

### D2: ETL script decomposition into package

**Decision**: Convert `scripts/etl_frbr_safe.py` into a `scripts/etl/` package with `__init__.py`, `reconcile.py`, `backup.py`, `merge.py`. The `__init__.py` re-exports the main entry point so `python scripts/etl_frbr_safe.py` continues to work via a thin wrapper or the `__init__.py` exposes `main()`.

**Rationale**: The ETL script has three distinct phases (reconciliation, backup verification, merge). Package decomposition mirrors the logical structure. A wrapper script at the original path preserves any cron/scheduler references.

**Alternative considered**: Keeping as single file with `# pylint: disable=too-many-lines`. Rejected because the safeguard tests would need updating, and the file is genuinely too large to maintain.

### D3: Dictionary dispatch for classify_operation()

**Decision**: Replace the 13-return if/elif chain in `app/api/sparql.py:73` with a dictionary mapping operation patterns to result tuples, with a single fallback return.

**Rationale**: Dictionary dispatch reduces cyclomatic complexity from 13 to 1, eliminates the `too-many-return-statements` warning, and makes the classification table data-driven and easier to extend.

**Alternative considered**: Strategy pattern with classes. Rejected as over-engineering for what is essentially a lookup table — the operations are pure data, not behavior.

### D4: Specific exception types for broad-exception-caught

**Decision**: Replace each `except Exception:` with the narrowest correct exception tuple:
- SPARQL query parsing: `except (ValueError, TypeError, KeyError):`
- Metrics counters: `except (ValueError, TypeError):`
- Subprocess operations: `except (OSError, subprocess.SubprocessError):`
- Test assertions: `except (AssertionError, ValueError):` or specific expected exceptions

**Rationale**: Each catch site has a known set of failure modes. Catching specific exceptions prevents masking unrelated bugs (e.g., `KeyboardInterrupt`, `SystemExit`).

**Alternative considered**: Creating custom exception hierarchy. Rejected as unnecessary complexity — the existing exception types are sufficient and well-understood.

### D5: Context managers for resource management

**Decision**: 
- `_query_semaphore.acquire()`: Wrap in `try/finally` with `release()` (semaphores don't support `with` in all Python versions for acquire with timeout)
- `_MP_CONTEXT.Pipe()`: Use `with` statement (Python 3.4+ supports this)
- `_MP_CONTEXT.Process()`: Use `with` statement for automatic `join()`/`terminate()`

**Rationale**: Context managers guarantee resource cleanup even on exceptions, eliminating the `consider-using-with` warning and preventing resource leaks.

**Alternative considered**: Manual try/finally for all three. Rejected because Pipe and Process natively support `with`, and using it is more idiomatic.

### D6: Type assertion for unsubscriptable-object

**Decision**: In `tests/test_etl_frbr_safe.py:412`, add an `assert isinstance(result, dict)` guard before the nested dict access, or restructure to use `.get()` with defaults.

**Rationale**: The warning arises because pylint can't prove the type. An explicit assertion satisfies the type checker and documents the expected shape.

## Risks / Trade-offs

- **[Re-export shim maintenance]** → Mitigation: Add a comment at the top of `public.py` explaining it's a compatibility shim. Consider adding a deprecation notice in a future release.
- **[Exception narrowing may miss edge cases]** → Mitigation: Run full test suite after each change. If a test fails due to an uncaught exception type, add it to the tuple — this is the correct behavior (making implicit failures explicit).
- **[Module split may break Flask blueprint registration]** → Mitigation: The re-export shim pattern guarantees all names remain available. Test with `pytest tests/test_api_*.py` after extraction.
- **[Dictionary dispatch changes error messages]** → Mitigation: Preserve the same return values and ensure any error logging in the original is maintained in the dispatch wrapper.
