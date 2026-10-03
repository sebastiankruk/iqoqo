## Context

PR #208 (`release/0.7.14`) completed its first round of expert reviews (Security, SRE, QA, Onto, UX, PM, TechComm, Dev) and a remediation batch was applied addressing 19 blocking issues. A second round of expert reviews (Security v2, SRE v2, QA v2) re-examined the post-fix codebase and identified 4 genuinely outstanding issues that were either newly discovered edge cases of the v1 SSRF fix or items that the first remediation batch missed entirely.

The 4 outstanding issues are all backend-only changes with no API contract modifications, no database migrations, and no frontend impact. They target `app/utils/http_client.py`, `app/core/tasks.py`, `app/utils/images.py`, `app/utils/llm_covers.py`, and `app/api/scanner.py`.

## Goals / Non-Goals

**Goals:**

- Close all 4 remaining security and stability findings before merging `release/0.7.14` to `main`
- Ensure all fixes pass existing `make test-backend`, `make lint`, and `make test-frontend` suites
- Add targeted test cases for each fix to prevent regression
- Maintain backward compatibility with all existing API contracts and client behavior

**Non-Goals:**

- Refactoring the overall SSRF protection architecture (already solid after v1 fixes)
- Addressing deferred v0.7.15 items (Alembic batch commits, Allegro E2E tests, rclone file permissions)
- Adding nginx configuration templates (deferred to v0.8.0)
- Modifying any frontend components or API endpoint signatures

## Decisions

### D1: Rclone `--` Delimiter Placement

**Decision**: Place all rclone flags (`--s3-no-check-bucket`) *before* the POSIX `--` end-of-options delimiter, then place file path arguments *after* it.

**Rationale**: The POSIX convention `--` signals "end of options" to the argument parser. Anything after `--` is treated as a literal operand, never as a flag. This prevents filenames starting with `-` (e.g., `--config=/etc/passwd`) from being interpreted as rclone command-line options.

**Alternatives Considered**:

- *Path prefixing* (prepend `./` to all paths): Fragile — doesn't work for absolute paths or remote targets like `iqoqo-glacier:archives/file.tar.gz`.
- *Input validation* (reject filenames with leading hyphens): Overly restrictive — legitimate filenames may start with hyphens in some locales.

### D2: DNS Resolution Timeout Strategy

**Decision**: Use `socket.setdefaulttimeout()` in a context manager pattern wrapping `socket.getaddrinfo()` calls, with a 5-second timeout.

**Rationale**: `socket.getaddrinfo()` has no direct timeout parameter. The standard Python approach is to temporarily set the default socket timeout. A 5-second timeout is generous enough for legitimate DNS servers but prevents indefinite worker thread blocking on malicious hanging DNS.

**Alternatives Considered**:

- *Threading with timeout*: More complex, potential resource leaks with orphaned threads. Overkill for DNS resolution which should complete in milliseconds.
- *`signal.alarm()`*: Only works on main thread, incompatible with Celery workers running in separate threads.

### D3: urljoin Type Coercion Approach

**Decision**: Apply `str()` coercion to both `current_url` and `next_url` before passing to `urllib.parse.urljoin()`.

**Rationale**: The `urljoin()` function strictly requires string arguments. While `response.headers.get("location")` normally returns a string, malformed proxies or mock objects in edge cases may yield non-string types. Defensive `str()` coercion adds negligible cost and prevents `TypeError` crashes in the Celery worker.

**Alternatives Considered**:

- *Type checking with explicit error*: Adds unnecessary branching complexity. The `str()` call is idempotent on strings.

### D4: Scanner Telemetry for Oversized Barcodes

**Decision**: Instead of silently returning (dropping telemetry), record the oversized barcode as a truncated entry with `status='rejected_oversized'` and log a warning. The barcode field stores the first 120 characters plus `"...(N)"` where N is the original length.

**Rationale**: Silent drops create audit blind spots. Recording the rejection with truncated content preserves the forensic trail for detecting injection attempts while respecting the 128-character column limit. The `status='rejected_oversized'` field allows analysts to filter and monitor for abuse patterns.

**Alternatives Considered**:

- *Raise an exception*: Would break the outer scan transaction, punishing the user for what might be an innocent camera mis-scan.
- *Hash the barcode*: Destroys the first N characters needed for pattern detection of injection attempts.

## Risks / Trade-offs

- **[Risk] DNS timeout may be too short for slow corporate networks** → Mitigation: 5 seconds is well above the 99th percentile for DNS resolution. Can be made configurable via environment variable in future if needed.
- **[Risk] `str()` coercion on `None` redirect location yields string `"None"`** → Mitigation: The existing `if not next_url` guard catches `None` before `str()` is ever called.
- **[Risk] Truncated barcode in telemetry may lose critical trailing characters** → Mitigation: The 120-char prefix plus total length indicator provides sufficient forensic context. Full payloads exceeding 128 chars are almost certainly injection attempts, not real barcodes.
