## Context

See `proposal.md` for problem motivation and scope.

Currently, FRBR F3 physical attributes have an inconsistent storage model:
- `Manifestation` in `app/db/core.py` has legacy definitions for `isbn13` and `publisher`, but physical format type is partially tracked via `format` and unstructured keys in `meta` (e.g. `meta["format_type"]`, `meta["publisher"]`, `meta["isbn13"]`).
- Ingestion pipelines often persist provider metadata into `meta` without populating typed columns.
- The v0.8.0 release milestone C2 requires standardizing physical attributes (`isbn13 VARCHAR(13) INDEXED`, `publisher VARCHAR(255)`, `format_type VARCHAR(50)`), migrating legacy JSONB `meta` entries, pruning migrated keys from JSONB, and ensuring full stack consistency across services, APIs, and frontend types.

## Goals / Non-Goals

**Goals:**
- Promote FRBR F3 physical attributes (`isbn13`, `publisher`, `format_type`) to typed relational columns on `catalog.manifestations`.
- Ensure appropriate B-tree indexes exist for `isbn13` (unique) and `format_type` / `publisher` for fast lookups and facet filtering.
- Provide a linear, reversible Alembic migration chained after `v0_7_18_fixes` that adds/aligns columns, backfills data from `meta` in safe batches, and deletes migrated keys from `meta`.
- Update `app/core/frbr_service.py` to write and read from typed columns directly.
- Maintain backward-compatible API responses in `app/api/manifestations.py` and schemas in `app/api/schemas.py`.
- Update TypeScript types in `frontend/types/frbr.ts`.

**Non-Goals:**
- Modifying FRBR Work (F1), Expression (F2), or Item (F4) schemas.
- Removing `raw_payload` (which retains untouched vendor ingestion payloads).
- Deprecating existing relational columns like `publication_date`, `cover_url`, `label`, `barcode`, or `catalog_number`.

## Decisions

### 1. Relational Schema & Column Definitions in `app/db/core.py`
- **Choice**:
  - `isbn13`: `db.Column(db.String(13), index=True, unique=True, nullable=True)`
  - `publisher`: `db.Column(db.String(255), nullable=True)`
  - `format_type`: `db.Column(db.String(50), index=True, nullable=True)`
- **Rationale**:
  - `isbn13` provides standard 13-character normalized ISBN lookups with unique indexing.
  - `publisher` constrained to standard length `VARCHAR(255)`.
  - `format_type` explicitly typed and indexed to support format faceting and filtering.
- **Alternatives Considered**: Keeping `format_type` in `meta` JSONB with a Postgres functional index. Rejected because JSONB lacks cross-dialect relational guarantees and increases serialization overhead.

### 2. Batched Migration & JSONB Pruning in Alembic
- **Choice**: Create a linear migration revision (`v0_7_19_f3_column_promotion`) following `v0_7_18_fixes`. The migration:
  1. Inspects `catalog.manifestations` (or default schema for SQLite).
  2. Alters `publisher` to `VARCHAR(255)` if needed, and adds `format_type VARCHAR(50)` and index `ix_catalog_manifestations_format_type`.
  3. Iterates in batches of 500 rows to extract:
     - `isbn13` from `meta ->> 'isbn13'` or `meta ->> 'isbn'`
     - `publisher` from `meta ->> 'publisher'` or `meta ->> 'Publisher'`
     - `format_type` from `meta ->> 'format_type'` or `meta ->> 'format'` or `meta ->> 'video_format'`
  4. Populates target columns if they are currently NULL.
  5. Removes migrated keys from `meta` (`meta - 'isbn13' - 'isbn' - 'publisher' - 'Publisher' - 'format_type'`).
  6. Implements a downgrade function that can copy column data back into `meta` before dropping `format_type`.
- **Rationale**: Batched processing prevents table locks during live upgrades; pruning migrated keys prevents split-brain state between columns and JSONB.
- **Alternatives Considered**: Immediate raw SQL UPDATE without batching. Rejected because large production datasets can lock the `manifestations` table and cause timeouts.

### 3. Service Layer Refactoring (`app/core/frbr_service.py`)
- **Choice**:
  - In `create_manifestation()`: Accept `format_type: str | None = None` (falling back to `meta.get("format_type")` or `meta.get("format")`). Persist to `manifestation.format_type`. Purge `format_type`, `isbn13`, `publisher` from `meta` dict before saving.
  - In `update_manifestation()`: Allow updating `format_type`, `isbn13`, `publisher` directly. Update the corresponding columns and synchronize or clean `meta`.
  - In `get_or_create_book_manifestation()`: Query `Manifestation.query.filter_by(isbn13=isbn)` against the typed column.
- **Rationale**: Keeps business logic aligned with the relational model and eliminates duplicate writes into `meta`.

### 4. API Serialization & Schema Compatibility
- **Choice**:
  - Update `app/api/manifestations.py` to include `"format_type": m.format_type` in `get_manifestations` and `get_manifestation_detail` responses.
  - Retain `"format": m.format_type or m.format` in response dictionaries to preserve backward compatibility for clients expecting `format`.
  - Update `ManifestationFrbrUpdateSchema` in `app/api/schemas.py` to validate `format_type: str | None = Field(default=None, max_length=50)`.
- **Rationale**: Seamless transition without breaking existing frontends or API integrations.

### 5. Frontend TypeScript Types (`frontend/types/frbr.ts`)
- **Choice**:
  - Add `format_type?: string;` to `Manifestation` and `CatalogEntry` interfaces.
  - Ensure `isbn13?: string;` and `publisher?: string;` are present on `Manifestation` and `CatalogEntry`.
- **Rationale**: Provides strict TypeScript compile-time checks across frontend views.

## Risks / Trade-offs

- **[Risk] Dirty or long data in legacy `meta` keys** → Mitigation: Backfill script sanitizes and truncates strings (e.g. `publisher[:255]`, `format_type[:50]`), strips hyphens from ISBNs, and logs warnings for malformed data.
- **[Risk] Downstream clients relying on `meta.isbn13` or `meta.publisher`** → Mitigation: API serializers surface `isbn13`, `publisher`, and `format_type` as top-level fields in JSON responses; serializers also maintain compatibility aliases if needed.
- **[Risk] Migration failure during JSONB key removal on SQLite vs Postgres** → Mitigation: Migration script detects database dialect (`bind.dialect.name == "postgresql"`) and uses dialect-appropriate JSON mutation logic.

## Migration Plan

1. Generate linear migration file `migrations/versions/v0_7_19_f3_column_promotion.py` with `down_revision = "v0_7_18_fixes"`.
2. Apply migration to test database (`flask db upgrade` or `alembic upgrade head`).
3. Verify all manifestation records have typed columns populated and `meta` stripped of redundant keys.
4. Execute test suite covering FRBR service, manifestation API routes, and schema validation.
5. Deploy backend and frontend together with backward-compatible API payload guarantees.
