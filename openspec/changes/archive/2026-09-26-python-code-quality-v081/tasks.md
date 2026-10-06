## 1. Module Decomposition — app/api/public.py

- [x] 1.1 Create `app/api/public_profile.py` by extracting profile-related route handlers and helpers from `app/api/public.py`. Verify the new module is importable and contains only profile-related code.
- [x] 1.2 Create `app/api/public_items.py` by extracting item-related route handlers and helpers from `app/api/public.py`. Verify the new module is importable and contains only item-related code.
- [x] 1.3 Create `app/api/public_rdf.py` by extracting RDF/linked-data route handlers and helpers from `app/api/public.py`. Verify the new module is importable and contains only RDF-related code.
- [x] 1.4 Replace `app/api/public.py` body with re-export shim: import all public names from the three new modules and re-export them. Verify `from app.api.public import *` still works and Flask blueprint registration succeeds.
- [x] 1.5 Run `pytest tests/test_public*.py tests/test_api*.py` and verify all existing tests pass with the decomposed modules.
- [x] 1.6 Run `pylint app/api/public.py app/api/public_profile.py app/api/public_items.py app/api/public_rdf.py` and verify no `too-many-lines` warning (each file ≤1000 lines).

## 2. Module Decomposition — scripts/etl_frbr_safe.py

- [x] 2.1 Create `scripts/etl/` package directory with `__init__.py`. Verify the package is importable.
- [x] 2.2 Create `scripts/etl/reconcile.py` by extracting reconciliation logic from `scripts/etl_frbr_safe.py`. Verify the module is importable and contains only reconciliation code.
- [x] 2.3 Create `scripts/etl/backup.py` by extracting backup verification logic from `scripts/etl_frbr_safe.py`. Verify the module is importable and contains only backup-related code.
- [x] 2.4 Create `scripts/etl/merge.py` by extracting merge/deduplication logic from `scripts/etl_frbr_safe.py`. Verify the module is importable and contains only merge-related code.
- [x] 2.5 Replace `scripts/etl_frbr_safe.py` with a thin wrapper that imports and calls `main()` from `scripts/etl/__init__.py`. Verify `python scripts/etl_frbr_safe.py --help` still works.
- [x] 2.6 Run `pytest tests/test_etl_frbr_safe.py` and verify all existing ETL tests pass with the decomposed modules.
- [x] 2.7 Run `pylint scripts/etl_frbr_safe.py scripts/etl/` and verify no `too-many-lines` warning (each file ≤1000 lines).

## 3. Strategy Pattern — classify_operation()

- [x] 3.1 Refactor `classify_operation()` in `app/api/sparql.py:73` from 13-return if/elif chain to dictionary dispatch mapping operation patterns to result tuples. Verify the function returns identical results for all known inputs.
- [x] 3.2 Run `pylint app/api/sparql.py` and verify no `too-many-return-statements` warning (returns ≤6).
- [x] 3.3 Run `pytest tests/test_sparql*.py` and verify all SPARQL-related tests pass with the refactored function.

## 4. Specific Exception Handling

- [x] 4.1 Replace `except Exception:` in `app/core/sparql_service.py` (18 occurrences) with specific exception tuples: `except (ValueError, TypeError, KeyError):` for query parsing, `except (ValueError, TypeError):` for metrics counters, `except (OSError, subprocess.SubprocessError):` for subprocess operations. Verify each replacement matches the actual failure modes at that site.
- [x] 4.2 Replace `except Exception:` in `app/api/sparql.py` (1 occurrence) with the appropriate specific exception tuple. Verify the replacement matches the actual failure mode.
- [x] 4.3 Replace `except Exception:` in test files (`tests/test_sparql_hardening.py`, `tests/test_public_rdf_safety.py`, `tests/test_sparql_timeout_regression.py`, `tests/test_sparql_adversarial.py`) with specific exception types that match what each test expects to catch. Verify tests still pass.
- [x] 4.4 Replace `except Exception:` in `scripts/etl_frbr_safe.py` (1 occurrence) with the appropriate specific exception tuple. Verify the replacement matches the actual failure mode.
- [x] 4.5 Run `pylint app/core/sparql_service.py app/api/sparql.py scripts/etl/ tests/test_sparql*.py tests/test_public_rdf_safety.py` and verify no `broad-exception-caught` warnings remain.
- [x] 4.6 Run `pytest tests/` and verify all tests pass — no test should fail due to an exception type no longer being caught.

## 5. Context Managers

- [x] 5.1 Wrap `_query_semaphore.acquire()` at `app/core/sparql_service.py:330` in a `try/finally` block ensuring `release()` is always called. Verify the semaphore behavior is unchanged under concurrent load.
- [x] 5.2 Wrap `_MP_CONTEXT.Pipe()` at `app/core/sparql_service.py:366` with a `with` statement. Verify pipe resources are properly cleaned up.
- [x] 5.3 Wrap `_MP_CONTEXT.Process()` at `app/core/sparql_service.py:367` with a `with` statement. Verify process lifecycle (join/terminate) is handled correctly.
- [x] 5.4 Run `pylint app/core/sparql_service.py` and verify no `consider-using-with` warnings remain.
- [x] 5.5 Run `pytest tests/test_sparql*.py` and verify all SPARQL service tests pass with the context manager changes.

## 6. Type Safety Fix

- [x] 6.1 Fix `unsubscriptable-object` warning at `tests/test_etl_frbr_safe.py:412` by adding an `assert isinstance(result, dict)` guard before the nested dict access `result["backup_verification"]["valid"]`, or restructure to use `.get()` with defaults. Verify the test still asserts the same behavior.
- [x] 6.2 Run `pylint tests/test_etl_frbr_safe.py` and verify no `unsubscriptable-object` warning remains.

## 7. Integration Verification

- [x] 7.1 Run `make lint-python` (or `pylint app/ scripts/ tests/`) and verify the overall pylint score is 10.00/10 with zero warnings.
- [x] 7.2 Run `pytest tests/test_lint_safeguards.py` and verify all safeguard tests pass (confirming no `# pylint: disable=` comments were added as a shortcut).
- [x] 7.3 Run `pytest tests/` and verify the complete test suite passes with no regressions.
- [x] 7.4 Verify backward compatibility: `python -c "from app.api.public import <key_names>"` succeeds for all previously exported names. Verify `python scripts/etl_frbr_safe.py --help` still works.
