## 1. Security Hotfix

- [x] 1.1 In `app/utils/http_client.py`, replace the `ThreadPoolExecutor` context manager in `_resolve_with_timeout` with an explicitly managed instance that calls `executor.shutdown(wait=False)` on exit.

## 2. Operations & SRE Hotfixes

- [x] 2.1 In `Makefile`, add `mkdir -p $(HOME)/.config/rclone` to the `dev` and `start` targets before calling Docker Compose / `run.sh` to ensure the host directory is safely pre-created.
- [x] 2.2 In `migrations/versions/e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill.py`, add `bind.execute(sa.text("COMMIT"))` for PostgreSQL inside the batch-processing loop after each chunk to immediately release transaction locks.

## 3. QA / E2E Hotfix

- [x] 3.1 In `frontend/__tests__/e2e/manual_verification_integration.spec.ts`, add `await page.route("**/api/auth/allegro/**", ...)` interceptor to the `beforeEach` hook to mock the Allegro OAuth polling endpoint and prevent test hangs.
