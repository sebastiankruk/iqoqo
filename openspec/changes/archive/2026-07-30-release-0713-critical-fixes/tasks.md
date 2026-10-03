## 1. API Security & Health Checks

- [x] 1.1 Update `app/api/system.py` to enforce `X-Deploy-Token` authentication for the `/api/health` endpoint.
- [x] 1.2 Update `app/core/data_manager.py` `verify_column_meta_drift()` to use `func.count()` aggregation instead of `.all()` to prevent OOM.

## 2. AI Cover Script Resiliency

- [x] 2.1 Update `scripts/generate_ai_covers.py` to check for `failed_llm_attempts >= 3` in item `meta` and skip if threshold is met.
- [x] 2.2 Update `scripts/generate_ai_covers.py` to increment `failed_llm_attempts` on failure and save the updated `meta`.
- [x] 2.3 Add `--force-retry` flag in `scripts/generate_ai_covers.py` to bypass the circuit breaker.

## 3. Database Migration Batching

- [x] 3.1 Locate Alembic migration `e3f891ab45c2` in `migrations/versions/`.
- [x] 3.2 Refactor the `upgrade()` function in `e3f891ab45c2` to perform batched updates using `LIMIT` and `OFFSET` loops.

## 4. API Schema Strictness

- [x] 4.1 Update `app/api/schemas.py` with strict Pydantic/Marshmallow validation for `kind`, `format`, `label`, `barcode`, and `catalog_number`.
- [x] 4.2 Update `app/api/admin.py` and `app/api/manifestations.py` to rely on the schema validation rather than loosely calling `data.get()`.

## 5. Housekeeping

- [x] 5.1 Update `docs/CHANGELOG.md` release date to `2026-07-30`.
- [x] 5.2 Delete the obsolete script `scripts/fix_manifestation_1984.py`.
- [x] 5.3 Fix the permission escalation issue in `frontend/components/admin/frbr-editor.tsx` so valid field edits are not discarded.
