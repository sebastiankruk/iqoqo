## 1. Rclone Permissions & Docker Isolation

- [x] 1.1 Update `deploy/Dockerfile` to copy `rclone.conf` with explicit `appuser` ownership and `0600` permissions. Verify by running `docker build` and ensuring the file permissions inside the resulting image are `0600` for user `10001`.
- [x] 1.2 Update `docker-compose.yml` to reflect correct mount configurations for `rclone.conf` ensuring non-root access. Verify by starting the backend service and asserting `rclone` can read its config.

## 2. Prebuilt Deployment & Docker Tagging

- [x] 2.1 Update `docker-compose.prebuilt.yml` to set `COMPOSE_PROJECT_NAME` implicitly via environment variables or explicit project settings (`iqoqo-prod` / `iqoqo-preview`) and change image tags to use explicit names like `iqoqo-backend:preview` and `iqoqo-frontend:preview` rather than `preiqoqo-*`. Verify by running `docker compose config` against it.
- [x] 2.2 Refactor `Makefile` targets `prod start prebuilt` and `preview start prebuilt` to only invoke `docker compose -f docker-compose.prebuilt.yml pull` and `up -d`. Verify these targets run successfully without requiring host node/python.
- [x] 2.3 Add logic in `Makefile` to output the current project version and the prebuilt tag version before deployment. Verify by running `make (prod|preview) start prebuilt` and checking the stdout for version info.
- [x] 2.4 Add automated dangling image pruning (`docker image prune -f --filter "dangling=true"`) to `Makefile` pre-deploy hooks. Verify by simulating a deploy and checking if `docker image prune` executes.

## 3. Resilient Redis Fallback

- [x] 3.1 Modify `app/__init__.py` to implement a `try/except` block checking Redis connectivity during startup (`redis.Redis(...).ping()`). Verify the code gracefully falls back to `memory://` for `RATELIMIT_STORAGE_URI` and `SimpleCache` for `CACHE_TYPE` if Redis is down.

## 4. Tests

- [x] 4.1 Create `tests/bats/test_makefile_prebuilt.bats` to test `make prod start prebuilt` without Python/Node present. Verify by running `bats tests/bats/test_makefile_prebuilt.bats` and seeing all tests pass.
- [x] 4.2 Create `tests/test_resilience.py` with pytest to simulate Redis connection drops during `app/__init__.py` execution and confirm Flask initializes with memory fallback. Verify by running `pytest tests/test_resilience.py` and seeing the tests pass.
