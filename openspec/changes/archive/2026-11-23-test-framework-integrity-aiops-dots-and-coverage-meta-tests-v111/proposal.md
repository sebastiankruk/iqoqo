## Why

A comprehensive audit of iqoqo's six testing tiers (Backend, Frontend, Scripts, E2E, Federation, and Semantics) and `Makefile` test entries uncovered structural gaps where tests are silently skipped or orphaned (`scripts/run_tests_parallel.py` ignoring `tests/` subdirectories, `make test-scripts-python` omitting `tests/scripts/`, `frontend/tests/e2e/*.spec.ts` sitting outside Playwright's `testDir`, `.github/workflows/quality.yml` skipping PostgreSQL FTS/trigger/merge suites, and `test-e2e-federation` falling back to `help_hub_workflow.spec.ts`), alongside `IQOQO_AI_MODE=1` regressions where several `Makefile` targets, Playwright, Vitest console logs, and the parallel runner emit walls of text instead of terse dots—with no meta-tests guarding suite discovery, coverage completeness, or `IQOQO_AI_MODE=1` dots-only output. Fixing these in `v1.1.1` (`C145`) ensures every test suite actually runs in local and CI pipelines and that `IQOQO_AI_MODE=1` remains strictly token-efficient and enforced by automated meta-tests.

## What Changes

- **`IQOQO_AI_MODE=1` Dots-Only Enforcement Across All Test Targets & Runners**:
  - Update `Makefile` targets (`test-backend-pg`, `test-e2e`, `test-e2e-db-up`, `_test-e2e-run`, `test-e2e-federation`, `test-merge-integrity-pg`) to use `$(PYTEST_FLAGS)` instead of hardcoded `-v`, suppress banner `echo` statements via `$(AI_ECHO)` / `[ "$(IQOQO_AI_MODE)" = "1" ]`, pipe `test-e2e-federation` BATS runs through `scripts/format_bats_ai.py`, and guard recursive make calls so `make -n` dry runs never execute live container/DB commands.
  - Update `frontend/vitest.config.ts` to suppress noisy `console.log`/`console.warn`/`console.error` output (`onConsoleLog: () => false`) when `IQOQO_AI_MODE=1` is set so `--reporter=dot` produces pure dots unless a test fails.
  - Update `frontend/playwright.config.ts` to select the `"dot"` reporter when `process.env.IQOQO_AI_MODE === "1"`.
  - Update `scripts/run_tests_parallel.py` (`make test-parallel` / `make test-fast` / `make test-stream-*`) to suppress `===` ASCII banners in `IQOQO_AI_MODE=1` and format BATS output via `scripts/format_bats_ai.py`.
- **Eliminate Silent Test Skips & Orphaned Suites**:
  - Update `scripts/run_tests_parallel.py` (`get_all_test_files()`) to recursively discover `tests/**/test_*.py` across subdirectories (`tests/core/`, `tests/integration/api/`, `tests/scripts/`) rather than only root `tests/test_*.py`.
  - Update `Makefile` `test-scripts-python` to include `tests/scripts/` alongside `tests/test_scripts.py` and `tests/test_script_utilities.py`.
  - Reconcile and move orphaned E2E specs from `frontend/tests/e2e/` (`admin-lod.spec.ts`, `friends-visibility.spec.ts`) into `frontend/__tests__/e2e/` so Playwright executes them.
  - Update `Makefile` `test-e2e-federation` fallback to execute standalone federation Playwright specs (`federation_multi_instance.spec.ts`, `federated_friend_request.spec.ts`, `federation_matrix_workflows.spec.ts`) rather than the unrelated `help_hub_workflow.spec.ts`.
  - Expand `.github/workflows/quality.yml` `test-postgres-gated` job to initialize all PostgreSQL schemas + `unaccent` extension and execute the PostgreSQL-gated FTS, trigger, and FRBR merge integrity suites (`tests/integration/db/test_fts_postgres.py`, `tests/test_search.py`, `tests/test_security_constraints.py`, `tests/test_frbr_merge_coverage.py`, `tests/test_frbr_merge_integrity.py`).
- **Meta-Tests for `IQOQO_AI_MODE=1` Dots-Only Output, Suite Discovery & Module Coverage**:
  - Expand `tests/test_aiops_mode.py` and `tests/bash/makefile_tooling.bats` with meta-tests verifying `Makefile` test targets, `vitest.config.ts`, `playwright.config.ts`, `scripts/format_bats_ai.py`, `scripts/run_tests_parallel.py`, and live subprocess dots-only output under `IQOQO_AI_MODE=1`.
  - Expand `tests/test_type_gate_and_suite_integrity.py` to scan **all** `tests/**/test_*.py` files for duplicate/shadowed test definitions, assert zero orphaned backend/script/frontend/E2E test files across `run_tests_parallel.py`, `test-scripts-python`, Vitest, and Playwright, and enforce module coverage mapping across `app/`, `scripts/`, and `frontend/`.
  - Add direct unit tests for previously unreferenced modules/scripts (`app/core/graph_service.py`, `app/core/wishlist_service.py`, `scripts/format_bats_ai.py`, `scripts/run_tests_parallel.py`, and uncovered frontend hooks/components/pages).

## Capabilities

### New Capabilities
- `testing/test-framework-and-aiops-integrity`: Enforces end-to-end test framework discovery integrity (zero orphaned backend/script/frontend/E2E suites, PostgreSQL CI gate completeness, federation E2E fallback fidelity, full-tree duplicate test-name detection, module coverage meta-tests) and strict `IQOQO_AI_MODE=1` dots-only output across all `Makefile` test targets and test runners.

### Modified Capabilities
- `script-test-coverage`: Expand `make test-scripts-python` and script test coverage requirements to include `tests/scripts/` and operational test runner scripts (`scripts/format_bats_ai.py`, `scripts/run_tests_parallel.py`).

## Impact

- **Build & CI Orchestration**: `Makefile`, `.github/workflows/quality.yml`, `scripts/run_tests_parallel.py`, `scripts/format_bats_ai.py`.
- **Frontend Test Config & Suites**: `frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `frontend/__tests__/e2e/`, `frontend/tests/e2e/`.
- **Backend & Meta-Test Suites**: `tests/test_aiops_mode.py`, `tests/test_type_gate_and_suite_integrity.py`, `tests/bash/makefile_tooling.bats`, plus new/expanded unit tests in `tests/` and `frontend/__tests__/`.
- **Release Planning**: `.context/notes/plan/1.1.x-release-plan.md` (`C145` registered under `v1.1.1`).
