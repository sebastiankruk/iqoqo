## 1. Stateless AI Covers (DevOps)

- [x] 1.1 Mount a Docker volume for `app/static/covers/` in deployment configurations so the container remains stateless
- [x] 1.2 Remove `boto3` logic from `scripts/generate_ai_covers.py` and `app/utils/llm_covers.py`, reverting to local file writes to the mounted volume
- [x] 1.3 Add `RCLONE_COVERS_REMOTE` to `.env.example`
- [x] 1.4 Implement `rclone` subprocess logic in generation scripts to optionally push/pull covers from the S3 global cache, logging a warning if unconfigured

## 2. Docker Build Optimization (DevOps)

- [x] 2.1 Refactor the main `Dockerfile` to use a multi-stage build (e.g., a `builder` stage for `pip install` and compiling extensions)
- [x] 2.2 Verify the final image copies only the necessary site-packages and app code
- [x] 2.3 Run a test build and verify the image size is < 500MB

## 3. Zero-Downtime Migrations (DevOps/QA)

- [x] 3.1 Modify Alembic migration `e3f891ab45c2` backfill logic
- [x] 3.2 Implement a chunking mechanism (using `LIMIT`/`OFFSET` or Primary Key iteration) updating 1000 rows at a time
- [x] 3.3 Add `time.sleep(0.1)` between chunked updates to yield DB locks

## 4. FTS Resilience Testing (QA)

- [x] 4.1 Define a list of malicious payloads (e.g., `%; DROP TABLE works; --`, `' OR 1=1 --`) in `tests/test_core_fixes.py`
- [x] 4.2 Write a parameterized pytest function that executes FTS searches using these payloads
- [x] 4.3 Verify the tests pass without executing the injection or crashing the API

## 5. Mapping Fragility Monitoring (Monitoring/Onto)

- [x] 5.1 Add OTel counter `mapping_parse_failures_total` in the application metrics registry
- [x] 5.2 Instrument the parsing logic that reads `shared/format_mappings.yaml` to increment this counter on miss
- [x] 5.3 Configure alerting rules (if applicable) for when the failure rate exceeds the acceptable threshold
