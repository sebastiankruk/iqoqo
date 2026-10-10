## 1. Local Gazetteer Database Tooling

- [x] 1.1 Create `scripts/init_geonames_db.py` to fetch `cities15000.zip`, unpack, and populate `data/geonames_cities.db` with indexed `cities` table; verify database builds successfully with >24,000 city records.
- [x] 1.2 Add `make init-geonames` target to `Makefile` with environment override support (`GEONAMES_DB_PATH`) and `--force` redownload/sync support; verify target runs idempotently.
- [x] 1.3 Verify Docker integration in `deploy/Dockerfile` / `docker-compose.yml` ensuring `data/geonames_cities.db` is accessible inside `worker` and `web` containers without host dependencies; verify container path resolution.
- [x] 1.4 Add GeoNames gazetteer health check to `scripts/iqoqo-status.sh` invoked by `make status`; verify `make status` reports gazetteer presence and row count (pass when ready, warn with sync instructions when missing/empty).

## 2. Offline-First Resolver Implementation

- [x] 2.1 Implement `GeoNamesClient._resolve_local(normalized_name)` in `app/core/lod_linking_service.py` to query SQLite with case-insensitive `name` and `asciiname` match ordered by `population DESC`; verify with test queries.
- [x] 2.2 Wire `GeoNamesClient.resolve_location` to check the local gazetteer first, fallback to remote API when missing, and gracefully log warnings on remote HTTP 401 / code 10 errors without raising unhandled exceptions; verify end-to-end resolution.

## 3. Test Suite Hardening

- [x] 3.1 Add unit tests in `tests/test_lod_linking.py` validating local gazetteer resolution, population-based disambiguation, missing database file fallback, and remote 401 error handling; verify with `pytest tests/test_lod_linking.py`.
- [x] 3.2 Run full LOD integration test suite (`tests/test_lod_linking.py`, `tests/test_admin_lod.py`, `tests/test_tasks_celery.py`) and verify all tests pass.

## 4. Code Quality & Formatting

- [x] 4.1 Run `make format-python` and verify Python formatting.
- [x] 4.2 Run `IQOQO_AI_MODE=1 make lint` and `make secret-scan` to verify CI compliance.
