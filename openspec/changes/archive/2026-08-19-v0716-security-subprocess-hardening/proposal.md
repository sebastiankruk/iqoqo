## Why

Four security-critical review findings from v0.7.14 v2/v3 reviews target the HTTP client (`app/utils/http_client.py`) and subprocess invocation layer (`app/core/tasks.py`, `app/utils/images.py`, `app/utils/llm_covers.py`). These patches harden the application against command option injection via crafted filenames, DNS-based thread starvation attacks, and TypeError DoS crashes in the SSRF-safe redirect loop.

**Note:** Code inspection reveals that several of these fixes are **already implemented** in the current codebase (POSIX `--` delimiters, `str()` coercion on `urljoin`, `executor.shutdown(wait=False)`, and `rejected_oversized` telemetry status). This spec validates that all fixes are complete, adds missing edge cases, and ensures comprehensive test coverage exists for each hardening measure.

## What Changes

- **Audit** all `subprocess.run(["rclone", ...])` calls across the codebase to confirm POSIX `--` end-of-options delimiter is present before user-controlled path arguments
- **Verify** `socket.getaddrinfo()` timeout enforcement in `_resolve_with_timeout()` — confirm explicit 5-second timeout and `shutdown(wait=False)` are in place
- **Verify** `str()` type coercion on `current_url` and `next_url` before `urljoin()` in the `safe_get()` redirect loop to prevent `TypeError` DoS
- **Add comprehensive tests** covering all four hardening measures — pytest unit tests for each defense pathway

## Capabilities

### New Capabilities

- `subprocess-hardening-audit`: Audit and test suite for POSIX `--` end-of-options across all subprocess invocations
- `http-client-resilience-tests`: Test suite validating DNS timeout enforcement, `str()` coercion, and ThreadPoolExecutor lifecycle

### Modified Capabilities

- `ssrf-prevention`: Adding test coverage for `str()` type coercion edge case in redirect loop
- `rclone-subprocess-hardening`: Verifying and testing POSIX `--` delimiter across all rclone subprocess calls

## Impact

- **Files:** `app/utils/http_client.py`, `app/core/tasks.py`, `app/utils/images.py`, `app/utils/llm_covers.py`
- **Tests:** New pytest tests in `tests/test_http_client.py` and `tests/test_subprocess_hardening.py`
- **Risk:** Low (most fixes already implemented; primary work is verification + test coverage)
- **Dependencies:** None — pure backend changes
