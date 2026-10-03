## Why

PR #208 (`release/0.7.14`) underwent a second round of expert reviews (Security, SRE, QA) after the first batch of fixes was applied. The v2 reviews identified 4 genuinely outstanding security and stability issues that were either newly discovered edge cases of the v1 SSRF fix or issues that the first remediation batch missed entirely. These must be resolved before merging to `main` because they represent exploitable attack vectors (command injection, worker DoS) and audit blind spots (silent telemetry loss).

## What Changes

- **Rclone command option injection prevention**: Add POSIX `--` end-of-options delimiter before path arguments in all `subprocess.run(["rclone", ...])` calls across `app/core/tasks.py`, `app/utils/images.py`, and `app/utils/llm_covers.py` to prevent maliciously crafted filenames starting with hyphens from being interpreted as rclone flags.
- **DNS resolution timeout enforcement**: Wrap `socket.getaddrinfo()` calls in `app/utils/http_client.py` with explicit timeouts to prevent Celery worker threads from blocking indefinitely when resolving malicious, infinitely-hanging DNS servers.
- **SSRF redirect handler type safety**: Add `str()` coercion to `current_url` and `next_url` before calling `urllib.parse.urljoin()` in the redirect loop of `safe_get()` to prevent `TypeError` crashes (DoS vector) when redirect headers yield non-string types.
- **Scanner telemetry audit gap closure**: Replace the silent `return` in `_record_scan_telemetry()` for oversized barcodes with proper warning logging and telemetry recording (truncated barcode with `status='rejected_oversized'`) to eliminate audit blind spots for injection attempts.

## Capabilities

### New Capabilities

- `rclone-subprocess-hardening`: POSIX-compliant end-of-options delimiter enforcement for all rclone subprocess invocations to prevent command flag injection via crafted file paths.

### Modified Capabilities

- `ssrf-prevention`: Add DNS resolution timeout enforcement to `socket.getaddrinfo()` calls within the SSRF-safe HTTP client to prevent worker thread starvation.
- `ssrf-redirect-protection`: Add `str()` type coercion to `urljoin()` arguments in the redirect-following loop to prevent `TypeError` DoS crashes on malformed redirect headers.
- `scanner-persistence`: Replace silent telemetry drop for oversized barcodes with auditable rejection recording to close the telemetry blind spot.

## Impact

- **Backend files modified**: `app/utils/http_client.py`, `app/core/tasks.py`, `app/utils/images.py`, `app/utils/llm_covers.py`, `app/api/scanner.py`
- **Security posture**: Closes 2 HIGH and 2 MEDIUM severity findings from second-round expert reviews
- **Test coverage**: New pytest cases for DNS timeout, type coercion in redirects, `--` delimiter in subprocess calls, and oversized barcode telemetry recording
- **No API contract changes**: All fixes are internal hardening — no endpoint signatures, response schemas, or migration changes
