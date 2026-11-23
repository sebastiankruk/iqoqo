# testing/test-framework-and-aiops-integrity Specification

## Purpose
Guarantees that iqoqo's multi-tier test suite (Backend Pytest, Frontend Vitest, BATS/Python Scripts, Playwright E2E, Federation, and Semantics) discovers and executes every test module without silent orphans or shadow definitions, enforces module-level test coverage across backend, script, and frontend boundaries, and emits strictly terse dots-only progress output under `IQOQO_AI_MODE=1` across all `Makefile` test targets and runners.

## Requirements

### Requirement: All Makefile test targets emit dots-only output under IQOQO_AI_MODE=1
The system SHALL ensure that every `Makefile` test target (`test-backend`, `test-backend-pg`, `test-frontend`, `test-scripts`, `test-scripts-python`, `test-scripts-bash`, `test-parallel`, `test-fast`, `test-streams`, `test-stream-domain`, `test-stream-api`, `test-stream-frontend`, `test-stream-tooling`, `test-merge-integrity-pg`, `test-e2e`, `test-e2e-federation`, and `test`) suppresses decorative `echo` banners and configures its underlying runner (`pytest`, `vitest`, `bats`, or `playwright`) to output terse dot progress (`.`) and a single concise summary when `IQOQO_AI_MODE=1` is set.

#### Scenario: Pytest targets use terse dot flags under IQOQO_AI_MODE=1

- **WHEN** `test-backend`, `test-backend-pg`, `test-scripts-python`, `test-merge-integrity-pg`, or `test-parallel` is invoked with `IQOQO_AI_MODE=1`
- **THEN** `pytest` SHALL run with `-q --tb=short --no-header` (and `verbose = -1`, `sugar` blocked via `conftest.py`) without `-v` overrides or decorative `echo` banners
- **THEN** passing tests SHALL emit only `.` characters followed by the concise pass summary line

#### Scenario: Vitest suppresses console spam and uses dot reporter under IQOQO_AI_MODE=1

- **WHEN** `test-frontend` (or `vitest run`) is executed with `IQOQO_AI_MODE=1`
- **THEN** Vitest SHALL use the `"dot"` reporter and suppress routine test `console.log`, `console.warn`, and `console.error` output (`onConsoleLog: () => false`) so passing runs emit only dot progress and the final summary

#### Scenario: BATS script targets pipe TAP output through format_bats_ai.py under IQOQO_AI_MODE=1

- **WHEN** `test-scripts-bash`, `test-parallel` (`stream_tooling`), or `test-e2e-federation` runs BATS suites with `IQOQO_AI_MODE=1`
- **THEN** BATS SHALL run with `--formatter tap` piped through `scripts/format_bats_ai.py`
- **THEN** passing BATS tests SHALL emit one `.` per test and `BATS: <N> tests passed.` without per-test titles

#### Scenario: Playwright E2E uses dot reporter under IQOQO_AI_MODE=1

- **WHEN** Playwright is invoked via `test-e2e` or `test-e2e-federation` with `IQOQO_AI_MODE=1`
- **THEN** `frontend/playwright.config.ts` SHALL include the `"dot"` console reporter alongside the non-interactive HTML report artifact

#### Scenario: Makefile dry-run does not execute live container or database commands

- **WHEN** `make -n <target> IQOQO_AI_MODE=1` is executed for any `test-*` target (including `test-e2e-federation` and `test-merge-integrity-pg`)
- **THEN** GNU Make SHALL print or dry-run the recipe without launching Docker containers or connecting to PostgreSQL

### Requirement: Meta-tests verify IQOQO_AI_MODE=1 dots-only behavior across Makefile and runners
The system SHALL include automated meta-tests in `tests/test_aiops_mode.py` and `tests/bash/makefile_tooling.bats` that verify both static `Makefile`/runner configurations and live subprocess output under `IQOQO_AI_MODE=1`.

#### Scenario: Static Makefile and runner configuration meta-test passes

- **WHEN** `pytest tests/test_aiops_mode.py` and `bats tests/bash/makefile_tooling.bats` run
- **THEN** the meta-tests SHALL assert that all `Makefile` `test-*` targets suppress banner `echo` statements, avoid hardcoded `pytest -v` when `IQOQO_AI_MODE=1`, wire `VITEST_FLAGS`, `PYTEST_FLAGS`, and `format_bats_ai.py`, and configure `dot` reporters in `vitest.config.ts` and `playwright.config.ts`

#### Scenario: Live subprocess meta-test enforces dots-only output

- **WHEN** the meta-test executes a sample `pytest` run and `scripts/format_bats_ai.py` TAP stream with `IQOQO_AI_MODE=1`
- **THEN** the captured stdout SHALL match strictly terse dot characters (`.`) plus the final one-line pass summary, with zero test function names or decorative headers

### Requirement: Test runners discover all backend, script, frontend, and E2E test suites without orphans
The system SHALL ensure that every test file in the repository is discovered and executed by its canonical test runner and `Makefile` target.

#### Scenario: Parallel test runner discovers subdirectory pytest suites

- **WHEN** `scripts/run_tests_parallel.py` partitions backend tests across `domain`, `api`, and `tooling` streams
- **THEN** it SHALL recursively include all `tests/**/test_*.py` files (including `tests/core/`, `tests/integration/api/`, and `tests/scripts/`), excluding only PostgreSQL-gated `tests/integration/db/` when `ENABLE_FTS_TESTS` is not `"true"`

#### Scenario: Playwright discovers all E2E specifications

- **WHEN** Playwright enumerates E2E tests under `frontend/__tests__/e2e/`
- **THEN** all E2E specifications (including `admin-lod.spec.ts` and `friends-visibility.spec.ts`) SHALL reside inside `frontend/__tests__/e2e/` and no orphaned `frontend/tests/e2e/` directory SHALL exist

#### Scenario: Federation E2E fallback executes federation specifications

- **WHEN** `make test-e2e-federation` runs in an environment where paired Docker preview containers cannot be started
- **THEN** the fallback verification SHALL run `tests/bash/verify_federation_preview.bats` and standalone federation Playwright E2E specs (`federation_multi_instance.spec.ts`, `federated_friend_request.spec.ts`, `federation_matrix_workflows.spec.ts`) rather than an unrelated non-federation spec

#### Scenario: CI PostgreSQL-gated job executes all PostgreSQL-specific test suites

- **WHEN** the `test-postgres-gated` job runs in `.github/workflows/quality.yml`
- **THEN** it SHALL initialize the required PostgreSQL schemas (`auth`, `catalog`, `inventory`, `social`, `federation`, `config`) and `unaccent` extension and execute `tests/test_migration_index_names.py`, `tests/integration/db/test_fts_postgres.py`, PostgreSQL FTS diacritic tests in `tests/test_search.py`, PostgreSQL trigger tests in `tests/test_security_constraints.py`, and `tests/test_frbr_merge_coverage.py` / `tests/test_frbr_merge_integrity.py`

### Requirement: Suite integrity and coverage meta-tests guard against shadowed tests and uncovered modules
The system SHALL enforce automated meta-tests in `tests/test_type_gate_and_suite_integrity.py` that fail whenever a test file defines duplicate/shadowed test names, a test file is orphaned from its runner, or an application/script module lacks test coverage references.

#### Scenario: Full-tree duplicate test definition scan

- **WHEN** `tests/test_type_gate_and_suite_integrity.py` runs
- **THEN** it SHALL parse every `tests/**/test_*.py` file via AST and assert that no module-level test function or test class/method name is defined more than once in the same file

#### Scenario: Orphaned test file detection

- **WHEN** `tests/test_type_gate_and_suite_integrity.py` runs
- **THEN** it SHALL assert that every `tests/**/test_*.py` file (outside `tests/integration/db/`) is partitioned by `scripts/run_tests_parallel.py`, every `tests/scripts/test_*.py` file is run by `make test-scripts-python`, and no E2E `.spec.ts` or `.test.ts` file exists outside `frontend/__tests__/e2e/`

#### Scenario: Backend, script, and frontend module coverage meta-test

- **WHEN** `tests/test_type_gate_and_suite_integrity.py` runs
- **THEN** it SHALL verify that every non-`__init__.py` Python module in `app/` (`app/api/`, `app/core/`, `app/db/`, `app/services/`, `app/strategies/`, `app/utils/`) and every operational script in `scripts/` is covered by or referenced in the test suite (or an explicit, bounded exemption list for non-runtime helpers), and that newly added unit tests cover `app/core/graph_service.py`, `app/core/wishlist_service.py`, `scripts/format_bats_ai.py`, `scripts/run_tests_parallel.py`, and previously uncovered frontend pages/components/hooks
