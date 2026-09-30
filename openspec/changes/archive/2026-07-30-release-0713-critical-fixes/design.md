## Context

The v0.7.13 release review surfaced several BLOCKING issues:

1. The `/api/health?check_drift=1` endpoint calls `.all()` on large tables, causing OOM and DoS vulnerabilities since it is unauthenticated.
2. `scripts/generate_ai_covers.py` violates statelessness by writing to local FS and wastes LLM tokens by endlessly retrying failures.
3. The Alembic migration `e3f891ab45c2` monolithic updates cause Postgres table locks leading to deployment timeouts.
4. Missing API schema validation on new metadata fields allows unvalidated data to reach the service layer.

## Goals / Non-Goals

**Goals:**

- Fix the OOM vulnerability in health checks by using SQL aggregation and requiring an `X-Deploy-Token` header.
- Prevent infinite LLM token waste in the AI cover generation script by adding a circuit breaker (failure counter in `meta` JSON).
- Prevent deployment timeouts by chunking the database migration updates.
- Ensure strict Pydantic/Marshmallow validation for all newly extracted API fields.

**Non-Goals:**

- Refactoring `generate_ai_covers.py` to use S3/cloud storage (deferred to v0.7.14, local writes will remain temporarily as an accepted risk as long as the circuit breaker is added).
- Full audit of all historical database migrations (only fixing `e3f891ab45c2`).

## Decisions

1. **Health Check Aggregation & Auth:** Use `func.count()` to aggregate the table differences in `verify_column_meta_drift()` instead of loading all rows via `.all()`. Add authentication via `X-Deploy-Token` to protect the route from public probes.
   - *Alternative:* Use `.yield_per(1000)` chunks (Security suggestion) - rejected because `func.count()` never loads rows into Python memory at all.
2. **AI Cover Circuit Breaker:** Track `failed_llm_attempts` in the manifestation's `meta` JSON. If the script sees `failed_llm_attempts >= 3`, skip the item unless `--force-retry` is passed.
3. **Migration Batching:** Refactor `e3f891ab45c2` to use `LIMIT` and `OFFSET` in a loop, committing or sleeping in between, avoiding full table locks.
4. **API Schema Strictness:** Update validation schemas to enforce strict types and constraints for `kind`, `format`, `label`, `barcode`, `catalog_number` before they hit the service layer.

## Risks / Trade-offs

- **[Risk]** Long-running migration could still delay deployment.
  - *Mitigation:* Chunking will keep the tables unlocked for regular application queries while the backfill happens in the background.
- **[Risk]** The `X-Deploy-Token` could be forgotten in existing monitoring tools.
  - *Mitigation:* Ensure deployment scripts and monitoring probes (like OpenObserve/Prometheus) are updated with the token.
