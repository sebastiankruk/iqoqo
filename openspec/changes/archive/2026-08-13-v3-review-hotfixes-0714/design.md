## Context

Three critical blockers were identified during the third round of QA/Security/SRE reviews for the 0.7.14 release:

1. **Security**: The SSRF DNS resolution timeout implementation using `concurrent.futures.ThreadPoolExecutor` as a context manager blocks the calling thread on exit, leading to potential worker starvation DoS.
2. **SRE**: The Alembic migration `e3f891ab45c2` processes rows in batches but lacks intermediate commits, holding transaction locks on the `works` and `manifestations` tables for the duration of the entire script on PostgreSQL.
3. **QA**: The `docker-compose.yml` mounts a host volume `~/.config/rclone`. If missing, Docker creates it as root, causing permission issues. Additionally, E2E tests for the Allegro flow lack a route interceptor for external API calls, causing potential test hangs.

## Goals / Non-Goals

**Goals:**

- Eliminate worker thread blocking in the SSRF DNS resolution timeout function.
- Release database locks frequently during the keyset pagination migration for FRBR columns.
- Ensure host directory pre-creation for Docker Compose mounts to avoid root ownership issues.
- Mock external Allegro authentication calls in Playwright E2E tests.

**Non-Goals:**

- Broader architectural changes to how external HTTP calls are made beyond the timeout issue.
- Refactoring the entire database migration strategy beyond adding `COMMIT` to this specific script.

## Decisions

- **ThreadPoolExecutor Management**: Explicitly instantiate `ThreadPoolExecutor` and use `executor.shutdown(wait=False)` in a `finally` block instead of a context manager. This ensures the calling Celery thread is freed immediately if the DNS call hangs, fulfilling the timeout's purpose.
- **Migration Commits**: Add `bind.execute(sa.text("COMMIT"))` after each batch in the PostgreSQL block of `migrations/versions/e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill.py`. This is safe because keyset pagination tracks progress by `last_id`, so partial failures can resume on retry.
- **Makefile Directory Creation**: Pre-create `$(HOME)/.config/rclone` in `run.sh` (which handles docker compose startup) or directly in `docker-compose.yml` pre-start targets. The Makefile `start` target calls `run.sh`, so we'll likely add it to the Makefile `dev` and `start` blocks or just before `docker-compose up` calls. Actually, `run.sh` line 754 does the `docker compose up`. The cleanest place per the review is the Makefile `dev` and `start` targets, or just `mkdir -p $(HOME)/.config/rclone` anywhere before `docker compose up`. We will inject it into `run.sh` or the Makefile where it starts containers. Wait, the review specifically asked: "Ensure pre-start targets in Makefile (dev, start) guarantee directory creation". We will add it to the Makefile.
- **Playwright Mocks**: Add `page.route("**/api/auth/allegro/**")` to `frontend/__tests__/e2e/manual_verification_integration.spec.ts` to mock the external Allegro API response.

## Risks / Trade-offs

- **Risk: Hanging DNS Threads Accumulating** -> **Mitigation**: The `ThreadPoolExecutor` is short-lived. The OS will eventually reap the thread when the socket times out at the TCP level or fails.
- **Risk: Partial Migration State** -> **Mitigation**: Since we commit in batches, a failure leaves the migration partially applied. However, the query uses `WHERE ... AND sort_title IS NULL`, so re-running the migration is idempotent and safe.
