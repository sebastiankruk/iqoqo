## Why

FRBR Group 1 Manifestations represent the physical embodiment of expressions. Physical attributes such as `isbn13`, `publisher`, and `format_type` have historically been stored inside unstructured JSONB `meta` dictionaries. This causes query performance bottlenecks on catalog filtering, lacks relational type safety, and complicates data validation across ingestion providers. Promoting these core physical attributes to explicit, typed SQLAlchemy columns with database indexes optimizes query performance, strengthens schema integrity, and establishes canonical typed access as part of the v0.8.0 release plan (C2: FRBR F3 Column Promotion).

## What Changes

- Add/enforce explicit typed SQLAlchemy columns on the `Manifestation` model in `app/db/core.py`:
  - `isbn13`: `VARCHAR(13)`, indexed, unique
  - `publisher`: `VARCHAR(255)`
  - `format_type`: `VARCHAR(50)`
- Create a linear Alembic migration chained after `v0_7_18_fixes` that:
  - Adds the new/adjusted columns and indexes to the `manifestations` table
  - Batch-backfills data from the JSONB `meta` column into the typed columns
  - Cleans up and removes the migrated keys (`isbn13`, `publisher`, `format_type`, and related legacy variations) from `meta`
  - Provides a reversible downgrade path
- Update `app/core/frbr_service.py` (`create_manifestation`, `update_manifestation`, and lookup queries) to read and write directly to typed columns instead of `meta`.
- Update API serializers and schemas in `app/api/manifestations.py` and `app/api/schemas.py` to maintain backward-compatible JSON responses while utilizing the typed columns.
- Update frontend TypeScript types in `frontend/types/frbr.ts` to include `isbn13`, `publisher`, and `format_type` on `Manifestation` and `CatalogEntry` interfaces.

## Capabilities

### New Capabilities
- `frbr/physical-attributes`: Explicit typed relational storage, indexing, migration, and service access for FRBR F3 Manifestation physical attributes (`isbn13`, `publisher`, `format_type`).

### Modified Capabilities
<!-- None: core FRBR ontology boundaries remain intact; this introduces the dedicated physical attributes storage capability -->

## Impact

- **Database**: `catalog.manifestations` table schema updated with `isbn13`, `publisher`, `format_type` columns and indexes; migration runs backfill and strips promoted keys from `meta`.
- **Backend Services**: `app/core/frbr_service.py` updated to use column-first reads and writes.
- **API**: `app/api/manifestations.py` and `app/api/schemas.py` serialize and validate typed columns without breaking existing client contracts.
- **Frontend**: `frontend/types/frbr.ts` updated with typed physical attribute properties.
