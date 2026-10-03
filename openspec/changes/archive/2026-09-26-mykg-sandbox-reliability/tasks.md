## 1. Proxy Synchronization

- [x] 1.1 Update `Makefile` target `mykg-update` to remove `--no-deps` from the `docker compose run` invocation. Verify: running `IQOQO_AI_MODE=1 make mykg-update` (when proxy is stopped) blocks on the "Waiting for proxy to be healthy" phase before starting the daemon.

## 2. Daemon Error Sentinel Implementation

- [x] 2.1 Update `.agents/skills/iqoqo-mykg/scripts/daemon_core.py` to add a `write_error_envelope(task_id: str, error_text: str, outbox_dir: Path)` function that writes the error text to `<task_id>.error` atomically using a temporary file. Verify: unit test passes validating that `<task_id>.error` is created containing the error text.
- [x] 2.2 Update `run_daemon` and `process_task` wrappers in both daemons (or `daemon_core.py` if centralized) to catch `subprocess.CalledProcessError` or general `Exception`s, invoke `write_error_envelope`, and return cleanly rather than crashing the worker. Verify: testing the daemon with an invalid command mock writes the `.error` file instead of hanging.

## 3. Orchestrator Monkeypatch

- [x] 3.1 Update `.agents/skills/iqoqo-mykg/scripts/run_update.py` to include a monkeypatch for `mykg.llm.agent_adapter.AgentAdapter.process_task` (or `_wait_for_sentinel` if extracted) that adds a check for `error_path.exists()` in the polling loop. If found, it should read the error file and raise `RuntimeError(f"Agent task {task_id} failed: {error_details}")`. Verify: running `python .agents/skills/iqoqo-mykg/scripts/run_update.py` imports and applies the patch without `AttributeError`s.

## 4. Tests and Verification

- [x] 4.1 Add test `test_write_error_envelope_atomic` in `tests/test_iqoqo_mykg.py` that verifies `.error` file creation. Verify: `IQOQO_AI_MODE=1 pytest tests/test_iqoqo_mykg.py -k "error_envelope"` passes.
- [x] 4.2 Add test `test_daemon_writes_error_on_failure` that mocks `subprocess.run` to raise an exception, processes a task, and asserts the `.error` sentinel exists in the outbox. Verify: test passes.
