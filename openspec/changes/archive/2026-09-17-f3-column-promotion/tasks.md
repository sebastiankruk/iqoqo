## 1. Database Model & Migration

- [x] 1.1 Update `Manifestation` model in `app/db/core.py` to declare explicit typed columns (`isbn13 VARCHAR(13) INDEXED UNIQUE`, `publisher VARCHAR(255)`, and `format_type VARCHAR(50) INDEXED`), verifying syntax and model imports with `python3 -c "from app.db.core import Manifestation"`
- [x] 1.2 Create linear Alembic migration in `migrations/versions/` chained after `v0_7_18_fixes` that adds/aligns `isbn13`, `publisher`, and `format_type` columns, creates indexes, batch-backfills values from `meta`, and prunes migrated keys from `meta`, verifying upgrade and downgrade execution on test database

## 2. FRBR Service Layer Updates

- [x] 2.1 Update `create_manifestation()` and `update_manifestation()` in `app/core/frbr_service.py` to persist `isbn13`, `publisher`, and `format_type` directly to typed columns and strip those keys from `meta`, verifying with `pytest tests/test_admin_frbr.py`
- [x] 2.2 Update manifestation lookup queries including `get_or_create_book_manifestation()` in `app/core/frbr_service.py` to query against typed columns, verifying with unit tests

## 3. API Serializers & Schema Validation

- [x] 3.1 Update Pydantic schemas in `app/api/schemas.py` (`ManifestationFrbrUpdateSchema`, `ManifestationUpdateSchema`) to validate `format_type` and length limits, verifying with schema validation tests
- [x] 3.2 Update API response serializers in `app/api/manifestations.py` (`get_manifestations` and `get_manifestation_detail`) to expose typed `format_type`, `isbn13`, and `publisher` while retaining backward-compatible `format`, verifying with API endpoint tests

## 4. Frontend Type Declarations

- [x] 4.1 Update `Manifestation` and `CatalogEntry` interfaces in `frontend/types/frbr.ts` to include `format_type?: string;` and ensure typed physical attributes, verifying TypeScript typing with `npm --prefix frontend run typecheck`

## 5. Verification & Regression Testing

- [x] 5.1 Add automated regression tests in `tests/` verifying data backfill, column-first retrieval, and JSONB `meta` key pruning
- [x] 5.2 Execute complete test and lint suite via `IQOQO_AI_MODE=1 make lint` to verify zero regressions across backend and frontend
