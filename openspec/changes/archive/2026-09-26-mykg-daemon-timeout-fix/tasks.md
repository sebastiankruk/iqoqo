## 1. Create Shared Daemon Core Module

- [x] 1.1 Create `.agents/skills/iqoqo-mykg/scripts/daemon_core.py` with the following shared functions extracted from `agy_daemon.py` and `opencode_daemon.py`: `REDACTED_PATTERNS` constant, `SECURITY_GUARDRAIL` constant, `sanitize_task_payload()`, `clean_json_fences()`, `compute_effective_timeout(task_timeout_seconds, prompt_length, default_timeout=300, base_timeout=600)`, `build_combined_prompt(task_data)`, `write_answer_envelope(task_id, answer_text, outbox_dir)`, `is_task_done(task_id, outbox_dir)`, `discover_tasks(inbox_dir, outbox_dir, submitted_tasks)`, and `run_daemon(inbox_dir, outbox_dir, process_fn, workers, poll_interval, model, effort)`. Verify: file exists and is importable with `python -c "import importlib.util; s=importlib.util.spec_from_file_location('dc','.agents/skills/iqoqo-mykg/scripts/daemon_core.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.compute_effective_timeout.__name__)"`.

- [x] 1.2 Implement `compute_effective_timeout(task_timeout_seconds: int | None, prompt_length: int, default_timeout: int = 300, base_timeout: int = 600) -> int` that returns `max(task_timeout_seconds or default_timeout, base_timeout + prompt_length // 1000)`. Verify: `compute_effective_timeout(1800, 72000)` returns `1800`, `compute_effective_timeout(None, 10000)` returns `610`, `compute_effective_timeout(None, 500)` returns `600`.

## 2. Refactor agy_daemon.py to Use Shared Core

- [x] 2.1 Refactor `agy_daemon.py` to import `sanitize_task_payload`, `clean_json_fences`, `SECURITY_GUARDRAIL`, `REDACTED_PATTERNS`, `compute_effective_timeout`, `build_combined_prompt`, `write_answer_envelope`, `is_task_done`, `discover_tasks`, and `run_daemon` from `daemon_core`. Remove all duplicated definitions. Keep only the agy-specific `process_task()` function that constructs the `agy` CLI command and calls `subprocess.run()`. Verify: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -k "agy" -x` passes all existing agy tests.

- [x] 2.2 Update `agy_daemon.py`'s `process_task()` to call `compute_effective_timeout(task_data.get("timeout_seconds"), len(combined_prompt))` instead of using the hardcoded `300` timeout. Verify: create a task JSON with `"timeout_seconds": 1800` and a 72KB prompt, mock `subprocess.run`, and assert the `timeout` kwarg passed to `subprocess.run` is `1800`.

## 3. Refactor opencode_daemon.py to Use Shared Core

- [x] 3.1 Refactor `opencode_daemon.py` to import shared functions from `daemon_core` and remove duplicated logic (sanitization patterns, guardrail, JSON fences, task discovery, answer writing, signal handling). Keep only the opencode-specific `_execute_task()` function (CLI construction, temp-file stdout redirect, effort-to-variant mapping, credential bootstrap). Verify: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -k "opencode" -x` passes all existing opencode tests.

- [x] 3.2 Update `opencode_daemon.py`'s `_execute_task()` to call `compute_effective_timeout(task_data.get("timeout_seconds"), len(combined_prompt))` instead of the local `base_timeout + prompt_timeout` formula. Verify: create a task JSON with `"timeout_seconds": 1800` and a 72KB prompt, mock `subprocess.run`, and assert the `timeout` kwarg is `1800`.

## 4. Tests for Shared Core

- [x] 4.1 Add a `daemon_core_module` pytest fixture to `tests/test_iqoqo_mykg.py` using the existing `_load_module` pattern to load `daemon_core.py`. Verify: fixture loads without import errors.

- [x] 4.2 Add test `test_compute_effective_timeout_honors_task_timeout` that asserts `compute_effective_timeout(1800, 72000)` returns `1800` (task timeout wins over dynamic formula `600 + 72 = 672`). Verify: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -k "test_compute_effective_timeout_honors_task_timeout" -x` passes.

- [x] 4.3 Add test `test_compute_effective_timeout_dynamic_formula` that asserts `compute_effective_timeout(None, 10000)` returns `610` (base 600 + 10 prompt bonus). Verify: test passes.

- [x] 4.4 Add test `test_compute_effective_timeout_base_floor` that asserts `compute_effective_timeout(None, 500)` returns `600` (base timeout floor when prompt is small and no task timeout). Verify: test passes.

- [x] 4.5 Add test `test_sanitize_task_payload_redacts_googleapis` that asserts a prompt containing `https://storage.googleapis.com/bucket/obj` is replaced with `[REDACTED_GOOGLEAPIS_URL]`. Verify: test passes.

- [x] 4.6 Add test `test_build_combined_prompt_prepends_guardrail` that asserts `build_combined_prompt({"system": "sys", "user": "usr"})` starts with the SECURITY_GUARDRAIL text and contains both "sys" and "usr". Verify: test passes.

- [x] 4.7 Add test `test_write_answer_envelope_atomic` that calls `write_answer_envelope("tid", '{"nodes":[]}', tmp_path)` and asserts both `.answer.json` and `.done` exist with correct content. Verify: test passes.

- [x] 4.8 Add test `test_agy_process_task_uses_task_timeout` that creates a task with `"timeout_seconds": 1800` and asserts the `timeout` kwarg passed to `subprocess.run` is `1800`. Verify: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -k "test_agy_process_task_uses_task_timeout" -x` passes.

- [x] 4.9 Add test `test_opencode_process_task_uses_task_timeout` that creates a task with `"timeout_seconds": 1800` and asserts the `timeout` kwarg passed to `subprocess.run` is `1800`. Verify: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -k "test_opencode_process_task_uses_task_timeout" -x` passes.

## 5. Final Verification

- [x] 5.1 Run full test suite: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -x` and verify all tests pass (existing + new). Verify: zero failures.

- [x] 5.2 Run `IQOQO_AI_MODE=1 make lint` on the three modified/created files and verify no lint errors. Verify: exit code 0.
