## Context

The iqoqo backend uses `subprocess.run()` to invoke `rclone` for cloud backup operations and a `ThreadPoolExecutor` for DNS resolution timeouts in the SSRF-safe HTTP client. v0.7.14 v2/v3 security reviews flagged four hardening gaps. Code inspection reveals that **all four fixes are already implemented** in the current codebase — this change focuses on verification and comprehensive test coverage.

Current state of each fix:

- `--` POSIX delimiter: Present in `tasks.py:189`, `images.py:128`, `llm_covers.py:356` ✅
- `shutdown(wait=False)`: Present in `http_client.py:68` ✅
- `str()` coercion on `urljoin`: Present in `http_client.py:261` ✅
- `rejected_oversized` telemetry: Present in `scanner.py:77` ✅ (tracked in Spec 2)

## Goals / Non-Goals

**Goals:**

- Verify all subprocess `rclone` invocations include POSIX `--` delimiter before user-controlled paths
- Verify DNS resolution timeout with explicit `shutdown(wait=False)` lifecycle
- Verify `str()` type coercion prevents `TypeError` in redirect loop
- Add comprehensive pytest coverage for each hardening measure
- Document each defense in test docstrings for future auditors

**Non-Goals:**

- Refactoring the HTTP client architecture (out of scope for hotfix)
- Adding new subprocess invocations
- Changing rclone integration patterns

## Decisions

### Decision 1: Audit-and-test approach over code changes
**Choice:** Since all four fixes are already implemented, this change is an audit + test coverage pass.
**Rationale:** Modifying already-correct code introduces unnecessary risk. Adding tests that codify the expected security behavior is the highest-value action.
**Alternative considered:** Re-implementing fixes from scratch — rejected as wasteful and risky.

### Decision 2: Separate test files by domain
**Choice:** Create `tests/test_subprocess_hardening.py` for rclone subprocess tests and extend `tests/test_http_client.py` for HTTP client tests.
**Rationale:** Keeps security tests discoverable and domain-aligned.

## Risks / Trade-offs

- **Risk:** Future developers add new `subprocess.run(["rclone", ...])` calls without `--` delimiter → **Mitigation:** Add a grep-based CI check or ruff custom rule that flags subprocess calls missing `--`
- **Risk:** `ThreadPoolExecutor` threads leak on repeated `shutdown(wait=False)` under heavy load → **Mitigation:** Monitor thread count in OTel telemetry; current single-worker executor limits blast radius
