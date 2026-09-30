---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:48Z
---

## 1. YAML Validation

- [x] 1.1 Create `scripts/validate_yaml.py` (or use inline bash/python) to parse `shared/format_mappings.yaml` using the built-in `yaml` module and exit 1 if a `yaml.YAMLError` occurs.
- [x] 1.2 Add a `validate-yaml` target to the `Makefile` that invokes the validation script.
- [x] 1.3 Update the main CI step (e.g., `make test` or `make lint`) to depend on `validate-yaml` so it runs automatically in the pipeline.

## 2. Telemetry Sanitization

- [x] 2.1 Update `app/core/telemetry.py` to add `"client-id"`, `"client_id"`, and `"api-key"` to the `sensitive_keywords` set in the `sanitize_headers` function.
- [x] 2.2 Write a test case in `tests/test_core_telemetry.py` ensuring that `Client-ID: xxxxx` and `Api-Key: yyyyy` are correctly transformed to `***REDACTED***` by `sanitize_headers`.

## 3. OAuth Concurrency Testing

- [x] 3.1 Create `frontend/__tests__/e2e/oauth_concurrency.spec.ts`.
- [x] 3.2 Write a Playwright test using `BrowserContext` to open 3 concurrent pages (`Promise.all([context.newPage(), context.newPage(), context.newPage()])`).
- [x] 3.3 Have all 3 pages navigate to the OAuth login trigger simultaneously.
- [x] 3.4 Assert the outcome of the race condition (either one succeeds and others gracefully redirect, or document the exact error state if it currently fails, to establish the baseline).
- [x] 3.5 Run `make test-e2e` (or equivalent Playwright command) to verify the test executes reliably.
