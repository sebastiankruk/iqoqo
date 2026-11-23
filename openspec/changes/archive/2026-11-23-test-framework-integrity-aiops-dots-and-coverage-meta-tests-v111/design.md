## Context

See `proposal.md` for motivation and scope. During the `v1.1.1` test-craftsman audit, six categories of test-framework defects were identified:
1. **`IQOQO_AI_MODE=1` wall-of-text leaks:** `test-backend-pg` hardcodes `pytest ... -v` and raw `@echo`; `test-e2e`, `test-e2e-db-up`, `_test-e2e-run`, `test-e2e-federation`, and `test-merge-integrity-pg` use raw `echo` banners; `frontend/playwright.config.ts` hardcodes `reporter: [["html", { open: "never" }]]`; `frontend/vitest.config.ts` uses `reporter: "dot"` under `IQOQO_AI_MODE=1` but allows noisy component `console.error`/`console.warn`/`console.log` spam to print; and `scripts/run_tests_parallel.py` prints `===` banners and runs unformatted BATS in `stream_tooling`.
2. **Make dry-run hazard (`make -n`):** `test-e2e-federation` and `test-merge-integrity-pg` embed `$(MAKE)` inside multi-line shell conditionals, causing GNU Make to execute the entire shell recipe even during `make -n` dry runs.
3. **Orphaned & skipped suites in local runners:**
   - `scripts/run_tests_parallel.py` (`get_all_test_files()`) uses `test_dir.glob("test_*.py")`, missing `tests/core/test_telemetry.py`, `tests/integration/api/test_llm_guards.py`, `tests/scripts/test_iqoqo_installer.py`, and `tests/scripts/test_verify_ai_cover_bindings.py`.
   - `Makefile` `test-scripts-python` runs only `tests/test_scripts.py tests/test_script_utilities.py`, omitting `tests/scripts/`.
   - `frontend/tests/e2e/admin-lod.spec.ts` and `frontend/tests/e2e/friends-visibility.spec.ts` sit outside Playwright's `testDir: "./__tests__/e2e"` while also being excluded from Vitest.
4. **CI PostgreSQL & Federation E2E coverage gaps:**
   - `.github/workflows/quality.yml` `test-postgres-gated` runs only `tests/test_migration_index_names.py`, leaving `tests/integration/db/test_fts_postgres.py`, PostgreSQL FTS/trigger tests in `test_search.py` / `test_security_constraints.py`, and FRBR merge integrity tests skipped across all CI jobs.
   - `Makefile` `test-e2e-federation` falls back to `help_hub_workflow.spec.ts` when paired preview containers cannot start on a standard GitHub runner, giving a false-green federation E2E check.
5. **Thin meta-tests & missing coverage meta-test:**
   - `tests/test_aiops_mode.py` only mocks `conftest.pytest_configure` (`2` unit tests).
   - `tests/test_type_gate_and_suite_integrity.py` checks duplicate test names only in `tests/test_account_deletion.py` and has no check for orphaned test files or uncovered modules.

## Goals / Non-Goals

**Goals:**
- Ensure every `Makefile` `test*` target and underlying test runner (`pytest`, `vitest`, `bats`, `playwright`, `run_tests_parallel.py`) produces terse dots-only output under `IQOQO_AI_MODE=1` and is safe under `make -n`.
- Eliminate all orphaned test files across `tests/core/`, `tests/integration/`, `tests/scripts/`, and `frontend/tests/e2e/`.
- Execute all PostgreSQL-gated backend tests in CI (`test-postgres-gated`) and run real federation E2E specs in the `test-e2e-federation` fallback path.
- Enforce automated meta-tests for `IQOQO_AI_MODE=1` dots-only compliance, full-tree duplicate test detection, zero orphaned test files, and module test coverage across `app/`, `scripts/`, and `frontend/`.
- Add direct unit tests for `app/core/graph_service.py`, `app/core/wishlist_service.py`, `scripts/format_bats_ai.py`, `scripts/run_tests_parallel.py`, and uncovered frontend hooks/components/pages.

**Non-Goals:**
- Changing production FRBR domain models, database migrations, or runtime API endpoints.
- Requiring live multi-container Docker Compose orchestration inside GitHub-hosted `ubuntu-latest` runners where prebuilt GHCR preview images and `/opt/pre.iqoqo` mounts are absent.

## Decisions

### 1. Unified `IQOQO_AI_MODE=1` Terse Output Contract Across All 4 Runners + Parallel Orchestrator
- **Pytest (`Makefile` & `conftest.py`):** Replace hardcoded `-v` in `test-backend-pg` with `$(PYTEST_FLAGS)` (`-q --tb=short --no-header` when `IQOQO_AI_MODE=1`, `-v` when unset). Replace raw `@echo` banners in `test-backend-pg`, `test-e2e-db-up`, `_test-e2e-run`, `test-e2e-federation`, and `test-merge-integrity-pg` with `$(AI_ECHO)` (or `[ "$(IQOQO_AI_MODE)" = "1" ] || echo ...` inside multi-line shell blocks).
- **Vitest (`frontend/vitest.config.ts`):** Keep `...(isAiMode ? { reporter: "dot", onConsoleLog: () => false } : {})`. Returning `false` from `onConsoleLog` in Vitest suppresses `console.log`/`warn`/`error` streams during passing tests while preserving assertion failure diffs and tracebacks when a test fails.
- **Playwright (`frontend/playwright.config.ts`):** Set `const isAiMode = process.env.IQOQO_AI_MODE === "1";` and `reporter: isAiMode ? [["dot"], ["html", { open: "never" }]] : [["html", { open: "never" }]]` so terminal output under `IQOQO_AI_MODE=1` is strictly dots while still writing the HTML report artifact for CI upload.
- **BATS & Parallel Runner (`scripts/run_tests_parallel.py` & `Makefile`):**
  - When `AI_MODE` is true in `scripts/run_tests_parallel.py`, run `bats --formatter tap tests/bash/` and format its output via `scripts/format_bats_ai.py`, suppress the 60-character `===` header/footer banners, emit compact per-stream dot/pass lines, and print full trailing failure logs only when a stream fails.
  - In `Makefile` `test-e2e-federation`, route the BATS check through `$(MAKE) test-scripts-bash` or `scripts/format_bats_ai.py` when `IQOQO_AI_MODE=1`.
- **Safe `make -n` Dry Runs:** Replace `$(MAKE)` inside multi-line shell blocks (`test-e2e-federation`, `test-merge-integrity-pg`) with `make` (or target prerequisites where appropriate) so GNU Make does not execute the shell block during `make -n` dry-run inspection.

### 2. Recursive Test Discovery & Orphan Elimination
- **`scripts/run_tests_parallel.py`:** Update `get_all_test_files()` to walk `ROOT / "tests"` recursively (`test_dir.rglob("test_*.py")`), returning POSIX paths relative to `ROOT` (e.g., `tests/core/test_telemetry.py`, `tests/scripts/test_iqoqo_installer.py`). Skip `tests/integration/db/` unless `os.environ.get("ENABLE_FTS_TESTS") == "true"` because `conftest.py` forces `sqlite:///:memory:` otherwise.
- **`Makefile` `test-scripts-python`:** Change `.venv/bin/pytest $(PYTEST_FLAGS) tests/test_scripts.py tests/test_script_utilities.py` to `.venv/bin/pytest $(PYTEST_FLAGS) tests/test_scripts.py tests/test_script_utilities.py tests/scripts/`.
- **Orphaned Frontend E2E Specs:**
  - Compare `frontend/tests/e2e/admin-lod.spec.ts` against `frontend/__tests__/e2e/admin-lod.spec.ts`; merge any unique test cases into `frontend/__tests__/e2e/admin-lod.spec.ts` and remove the duplicate `frontend/tests/e2e/admin-lod.spec.ts`.
  - Move `frontend/tests/e2e/friends-visibility.spec.ts` to `frontend/__tests__/e2e/friends-visibility.spec.ts` and remove the empty `frontend/tests/e2e/` directory.

### 3. CI `test-postgres-gated` & `test-e2e-federation` Hardening
- **`.github/workflows/quality.yml` (`test-postgres-gated`):** After running `tests/test_migration_index_names.py`, create a dedicated `iqoqo_pg_gated` database (or use `postgres`) with schemas `auth`, `catalog`, `inventory`, `social`, `federation`, `config` and `CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public`, then run:
  ```bash
  ENABLE_FTS_TESTS=true DATABASE_URL="postgresql://postgres:postgres@localhost:5432/iqoqo_pg_gated" \
    pytest tests/integration/db/test_fts_postgres.py \
      tests/test_search.py -k "postgres_fts" \
      tests/test_security_constraints.py -k "postgres_lending_trigger" \
      tests/test_frbr_merge_coverage.py tests/test_frbr_merge_integrity.py -v -p no:randomly
  ```
  (Wait: in `pytest` CLI, `-k` filters all collected files if passed together; running `test_fts_postgres.py`, `test_frbr_merge_coverage.py`, `test_frbr_merge_integrity.py`, `test_search.py`, and `test_security_constraints.py` in two clean invocations ensures every test in those files runs against PostgreSQL!).
- **`Makefile` (`test-e2e-federation`):** In the fallback branch (when `iqoqo-preview-peer-web-1` is not running), replace `__tests__/e2e/help_hub_workflow.spec.ts` with `__tests__/e2e/federation_multi_instance.spec.ts __tests__/e2e/federated_friend_request.spec.ts __tests__/e2e/federation_matrix_workflows.spec.ts`, which mock/exercise multi-instance federation flows against the Playwright-spawned test server.

### 4. Meta-Tests for `IQOQO_AI_MODE=1`, Suite Integrity & Coverage Completeness
- **`tests/test_aiops_mode.py`:**
  - Keep existing `pytest_configure` unit tests.
  - Add unit tests for `scripts/format_bats_ai.py` (`main()` with passing TAP, failing TAP, and non-TAP error output).
  - Add unit tests for `scripts/run_tests_parallel.py` verifying `AI_MODE` flag propagation (`-q --tb=short --no-header`, `--reporter=dot`, `format_bats_ai.py`) and banner suppression.
  - Add static contract tests verifying `Makefile` `test-*` targets, `frontend/vitest.config.ts` (`reporter: "dot"`, `onConsoleLog`), and `frontend/playwright.config.ts` (`dot` reporter when `IQOQO_AI_MODE === "1"`).
  - Add a live subprocess test running `pytest tests/test_version.py` with `IQOQO_AI_MODE=1` and asserting stdout contains only dots (`.`) and the single-line `N passed in ...s` summary (no `===` header, no platform info, no test names).
- **`tests/test_type_gate_and_suite_integrity.py`:**
  - Widen `test_no_test_class_or_function_is_defined_twice_in_one_file` to scan `sorted(TESTS_DIR.rglob("test_*.py"))` across the entire `tests/` tree.
  - Add `test_all_backend_test_files_are_discovered_by_parallel_runner_and_script_targets` asserting zero orphaned `tests/**/test_*.py` files.
  - Add `test_all_frontend_e2e_specs_live_inside_playwright_test_dir` asserting `frontend/tests/e2e` does not exist and every E2E spec is inside `frontend/__tests__/e2e`.
  - Add `test_module_coverage_across_app_scripts_and_frontend` verifying that every Python module in `app/` and operational script in `scripts/` (plus frontend routes/components/hooks, subject to a small explicit documented allowlist for pure static/legal/type barrels) is imported or referenced by at least one test file.

## Risks / Trade-offs

- **[Risk] Newly widened full-tree duplicate test-name scan in `test_type_gate_and_suite_integrity.py` may uncover existing duplicate test function names in other `tests/test_*.py` files** → *Mitigation:* Run the AST scan across all `tests/**/test_*.py` during implementation and rename any shadowed duplicate test functions so every test actually executes.
- **[Risk] Relocating `frontend/tests/e2e/friends-visibility.spec.ts` into `frontend/__tests__/e2e/` adds it to live CI `test-e2e` runs** → *Mitigation:* Audit and verify `friends-visibility.spec.ts` and `admin-lod.spec.ts` so their selectors and route mocks pass deterministically under Playwright Chromium.
- **[Risk] Suppressing console output in Vitest under `IQOQO_AI_MODE=1` could hide logs needed when debugging a failing test** → *Mitigation:* Only set `onConsoleLog: () => false` when `IQOQO_AI_MODE` is enabled; standard mode (`IQOQO_AI_MODE` unset) retains full console output, and Vitest always prints full assertion diffs and stack traces on failure.
