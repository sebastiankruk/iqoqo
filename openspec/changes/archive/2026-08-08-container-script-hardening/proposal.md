## Why

Based on recent reviews (DevOps, QA, and Onto), our platform requires several operational and resilience improvements. We need to enforce container statelessness, reduce image footprint, ensure database migrations don't cause downtime, prove our Full Text Search (FTS) is immune to injection attacks, and proactively monitor external metadata mapping fragility.

## What Changes

- Refactor `scripts/generate_ai_covers.py` to write covers to a mounted Docker volume instead of directly into the stateless image. Add an optional global S3 cache synced via `rclone` (using `RCLONE_COVERS_REMOTE`) to share generated covers across iQoQo instances.
- Optimize the Docker build process using multi-stage builds to shrink the final image size below 500MB.
- Refactor the Alembic migration `e3f891ab45c2` (backfill) to use chunked/batched `LIMIT`/`OFFSET` loops with sleep intervals, ensuring zero-downtime when processing large datasets.
- Add chaos/injection payloads (e.g., `%; DROP TABLE works; --`) to `tests/test_core_fixes.py` to verify FTS resilience.
- Introduce OpenObserve telemetry (OTel) to track the fragility of Blu-ray audio format mappings from external sources (MusicBrainz/Discogs) in `shared/format_mappings.yaml`.

## Capabilities

### New Capabilities

- `stateless-ai-covers`: Stateless handling of AI covers by persisting them to a mounted Docker volume, with an optional global cache via `rclone` S3 sync.
- `docker-build-optimization`: Optimized, multi-stage Docker builds resulting in smaller (<500MB) images.
- `zero-downtime-migrations`: Batching and chunking logic in Alembic migrations to support zero-downtime data backfills.
- `fts-resilience-testing`: Automated chaos and injection testing suite for Full Text Search queries.
- `mapping-fragility-monitoring`: OpenObserve alerts and OTel metrics on unexpected structural changes to metadata format strings from third-party APIs.

### Modified Capabilities

## Impact

- `scripts/generate_ai_covers.py`
- `Dockerfile` (and related build scripts)
- Alembic migration scripts (specifically `e3f891ab45c2`)
- `tests/test_core_fixes.py`
- Monitoring infrastructure and `shared/format_mappings.yaml` processing logic.
