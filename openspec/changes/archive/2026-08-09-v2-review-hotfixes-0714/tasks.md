## 1. Rclone Subprocess Hardening

- [x] 1.1 In `app/core/tasks.py`, reorder the `subprocess.run()` call in `upload_to_glacier()` to place `--s3-no-check-bucket` before the `--` end-of-options delimiter and file path arguments after it: `["rclone", "copy", "--s3-no-check-bucket", "--", file_path, target]`
- [x] 1.2 In `app/utils/images.py`, reorder the `subprocess.run()` call for rclone cover upload to use the `--` delimiter: `["rclone", "copyto", "--s3-no-check-bucket", "--", filepath, target]`
- [x] 1.3 In `app/utils/llm_covers.py`, reorder the `subprocess.run()` call for rclone cover download to use the `--` delimiter: `["rclone", "copyto", "--s3-no-check-bucket", "--", target, local_file]`
- [x] 1.4 Add pytest tests in `tests/test_rclone_hardening.py` verifying that all 3 subprocess calls include the `--` delimiter before path arguments (mock `subprocess.run` and assert argument order)

## 2. DNS Resolution Timeout Enforcement

- [x] 2.1 In `app/utils/http_client.py`, wrap the `socket.getaddrinfo()` call at line ~103 (`is_safe_url` function) with a `socket.setdefaulttimeout(5)` context manager or try/finally pattern, catching `socket.timeout` and raising `SSRFError`
- [x] 2.2 In `app/utils/http_client.py`, wrap the `socket.getaddrinfo()` call at line ~197 (`SSRFProtectionAdapter` / connection pinning) with the same timeout pattern
- [x] 2.3 Add pytest tests in `tests/test_ssrf_dns_timeout.py` verifying that a hanging DNS resolution raises `SSRFError` within 5 seconds (mock `socket.getaddrinfo` to simulate hang with `time.sleep`)

## 3. SSRF Redirect Handler Type Safety

- [x] 3.1 In `app/utils/http_client.py`, update the redirect loop in `safe_get()` to coerce arguments: `current_url = urljoin(str(current_url), str(next_url))`
- [x] 3.2 Add pytest test in `tests/test_ssrf_redirect_type_safety.py` verifying that `safe_get()` does not raise `TypeError` when a redirect `Location` header yields a bytes or non-string type (mock response with bytes location header)

## 4. Scanner Telemetry Audit Gap

- [x] 4.1 In `app/api/scanner.py`, replace the silent `return` in `_record_scan_telemetry()` for oversized barcodes with: truncate to first 120 chars + `"...(N)"` suffix, set `status='rejected_oversized'`, log warning, and proceed with recording
- [x] 4.2 Add pytest test in `tests/test_scanner_telemetry.py` verifying that a 200-character barcode produces a `ScanTelemetry` record with `status='rejected_oversized'` and truncated barcode, not a silent drop

## 5. Validation and Cleanup

- [x] 5.1 Run `make lint` and fix any new warnings or errors
- [x] 5.2 Run `make test-backend` and ensure all existing + new tests pass
- [x] 5.3 Update `docs/CHANGELOG.md` with v2 review hotfix entries under the 0.7.14 section
