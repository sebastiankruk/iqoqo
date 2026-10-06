## Why

This change addresses the final critical blockers identified in the v3 QA, SRE, and Security reviews for the 0.7.14 release. Resolving these issues ensures secure and non-blocking background task execution, reliable directory creation for container mounts, unblocked production database migrations, and stable Playwright E2E testing environments.

## What Changes

- Removes the context manager for `concurrent.futures.ThreadPoolExecutor` in the SSRF DNS resolution timeout logic (`app/utils/http_client.py`) and uses `executor.shutdown(wait=False)` to prevent worker thread blocking/starvation DoS.
- Adds `mkdir -p $(HOME)/.config/rclone` to the `start` and `dev` execution paths in `Makefile` to guarantee the required directory exists on the host before Docker Compose mounts it, avoiding root-owned directory permission errors.
- Modifies the Alembic migration `e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill.py` to include explicit `COMMIT` statements within its batch-processing keyset loop, preventing PostgreSQL from holding long transaction locks over the entire migration duration.
- Adds `page.route("**/api/auth/allegro/**")` intercept/mock to Playwright E2E configuration (`frontend/__tests__/e2e/manual_verification_integration.spec.ts`) to prevent test runner hangs when polling for the Allegro device flow.

## Capabilities

### New Capabilities

### Modified Capabilities

- `rclone-subprocess-hardening`: Ensure the host rclone configuration directory exists before container startup.
- `review-fixes-data-integrity`: Release PostgreSQL backfill locks after each migration batch.
- `allegro-oauth`: Mock Allegro OAuth polling in E2E verification so tests do not depend on the external service.

## Impact

- `app/utils/http_client.py`: Thread management modified.
- `Makefile`: Directory creation sequence updated.
- `migrations/versions/e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill.py`: Database transaction scope adjusted.
- `frontend/__tests__/e2e/manual_verification_integration.spec.ts`: Test mocking updated.
