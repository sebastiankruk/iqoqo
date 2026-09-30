## Context

Review findings across DevOps, QA, and Onto teams identified several areas where our infrastructure and tests need hardening. The `generate_ai_covers.py` script writes to the local filesystem, breaking container statelessness. The Docker image is bloated, slowing deployments. Data backfills (like `e3f891ab45c2`) cause long locks and downtime on large datasets. Full Text Search (FTS) lacks explicit chaos testing to prove it won't crash on malicious input. Finally, we lack visibility into when external data providers alter specific string formats, which silently breaks parsing.

## Goals / Non-Goals

**Goals:**

- Mount a Docker volume for AI covers to keep the container stateless, and use `rclone` for optional global S3 caching.
- Refactor the `Dockerfile` into a multi-stage build to strip out build dependencies, targeting an image size under 500MB.
- Rewrite the Alembic migration `e3f891ab45c2` to use batched chunking (`LIMIT`/`OFFSET` or primary key ranges) with sleeps.
- Implement SQL injection and chaos payloads in `tests/test_core_fixes.py` against FTS inputs.
- Add OpenObserve OTel gauge/counters that monitor mapping parsing failures in `shared/format_mappings.yaml`.

**Non-Goals:**

- Completely rewriting the AI cover generation logic itself (only changing the output destination).
- Rewriting all past migrations (only targeting the problematic `e3f891ab45c2` and establishing a pattern for future backfills).

## Decisions

### 1. Multi-stage Docker Builds

- **Decision**: Use a "builder" stage to compile dependencies (e.g., building wheels, compiling C extensions) and a "runtime" stage that only copies the compiled artifacts and runtime dependencies. Use an `alpine` or `slim` base image.
- **Rationale**: This drastically reduces the image size, speeding up pull times and reducing the attack surface.

### 2. Zero-Downtime Alembic Migrations

- **Decision**: For `e3f891ab45c2` (and future backfills), the script will execute a loop that updates 1000 rows at a time based on Primary Key ranges, followed by a `time.sleep(0.1)` to yield database locks.
- **Rationale**: Updating millions of rows in a single transaction locks the table, causing application downtime. Chunking prevents this.

### 3. FTS Resilience Testing

- **Decision**: Add parameterized tests to `pytest` using a predefined list of SQL injection and chaos strings (e.g., `%; DROP TABLE`, `' OR 1=1 --`).
- **Rationale**: Proves that the application correctly parameterizes and sanitizes search queries before passing them to the PostgreSQL FTS engine.

## Risks / Trade-offs

### 4. Two-Tier Storage for AI Covers

- **Decision**: Primary storage for AI covers will be a local Docker volume mounted to the container. Secondary storage will be an optional S3 global cache synced via `rclone` and the `RCLONE_COVERS_REMOTE` environment variable.
- **Rationale**: Direct S3 uploads via `boto3` incur unnecessary AWS costs and split the storage mechanisms. A Docker volume keeps the image small and stateless while persisting data locally. Using `rclone` allows caching for multi-instance deployments without failing if not configured.

- [Risk] **Missing S3 cache configuration** → Mitigation: Gracefully fallback to local-only generation with a simple warning if `rclone` is unconfigured.
- [Risk] **Multi-stage builds miss a dynamic runtime dependency** → Mitigation: Thorough integration testing of the final stripped image in CI before merging.
