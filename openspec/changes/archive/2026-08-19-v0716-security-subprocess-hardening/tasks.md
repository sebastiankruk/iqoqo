## 1. Audit Subprocess Calls

- [x] 1.1 Grep all `subprocess.run` calls in `app/` to create exhaustive inventory of subprocess invocations
- [x] 1.2 Verify `--` delimiter present before user-controlled paths in `app/core/tasks.py` (line 189)
- [x] 1.3 Verify `--` delimiter present before user-controlled paths in `app/utils/images.py` (line 128)
- [x] 1.4 Verify `--` delimiter present before user-controlled paths in `app/utils/llm_covers.py` (line 356)
- [x] 1.5 Check for any additional `subprocess.run` calls in `app/` missing the `--` delimiter

## 2. Audit HTTP Client Hardening

- [x] 2.1 Verify `_resolve_with_timeout()` in `app/utils/http_client.py` uses `executor.shutdown(wait=False)` (line 68)
- [x] 2.2 Verify `str()` coercion applied to both `current_url` and `next_url` before `urljoin()` in `safe_get()` (line 261)
- [x] 2.3 Verify explicit 5-second timeout parameter in `_resolve_with_timeout()` calls

## 3. Write Test Suite

- [x] 3.1 Create `tests/test_subprocess_hardening.py` with tests verifying `--` delimiter in all rclone subprocess calls
- [x] 3.2 Add tests to `tests/test_http_client.py` for DNS timeout enforcement (mock `socket.getaddrinfo` with delay)
- [x] 3.3 Add tests for `str()` coercion edge case — pass non-string URL to redirect handler
- [x] 3.4 Add tests for `ThreadPoolExecutor.shutdown(wait=False)` lifecycle verification

## 4. Verification

- [x] 4.1 Run `make format-python`
- [x] 4.2 Run `make lint-python` — verify no errors
- [x] 4.3 Run `make test-backend` — verify all tests pass
- [x] 4.4 Document audit findings in PR description
