## Why

This change is required to address BLOCKING issues from the v0.7.13 release reviews that must be fixed before the release can ship. These issues span critical security vulnerabilities (DoS via unauthenticated health endpoint triggering OOM), statelessness violations (local filesystem writes in scripts), database locking during migrations, and API schema validation gaps.

## What Changes

- Protect health endpoint with `X-Deploy-Token` and replace `.all()` with `func.count()` aggregation to prevent OOM.
- Implement circuit breaker in AI cover generation script to limit retries and prevent rate limits.
- **BREAKING**: Refactor migration `e3f891ab45c2` to chunked updates to prevent database locking.
- Enforce strict Pydantic/Marshmallow validation for new API schema fields.
- Fix minor housekeeping issues: changelog dates, removing obsolete scripts, and frontend permission escalation bugs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `observability-health-validation`: The health check behavior is changing to require token authentication and use aggregation instead of full row loading to prevent OOM/DoS.
- `batch-watermarking`: The AI cover generation script is changing to track failures (circuit breaker) and prevent infinite retry loops that waste tokens.
- `relational-metadata-normalization`: Migration behavior is changing to batch/chunk updates rather than locking tables monolithically.

## Impact

- `app/api/system.py` and `app/core/data_manager.py` (Health check API and core DB calls)
- `scripts/generate_ai_covers.py` (AI cover batch job)
- `migrations/versions/e3f891ab45c2*.py` (Alembic migration logic)
- `app/api/admin.py`, `app/api/manifestations.py`, `app/api/schemas.py` (API validation layer)
- `frontend/components/admin/frbr-editor.tsx` (Frontend editor permissions)
- `docs/CHANGELOG.md` (Release dates)
