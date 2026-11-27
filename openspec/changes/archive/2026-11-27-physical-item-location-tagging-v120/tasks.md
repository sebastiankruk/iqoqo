## 1. Database Schema & FRBR `Item` Model (`app/db/`)

- [x] 1.1 Add `physical_location = db.Column(db.String(255), nullable=True, index=True)` to `Item` in `app/db/core.py` and gate `Item.to_dict()` / item serialization so `physical_location` is returned only to the owner (or admin)
- [x] 1.2 Generate a single linear Alembic migration (`len(revision) <= 32`) adding `physical_location` and its index on `inventory.items`

## 2. Backend API, Filtering, Bulk Update & RDF (`app/api/`, `app/core/`)

- [x] 2.1 Support `physical_location` updates in `PATCH /api/items/<id>` and add `PATCH /api/items/bulk-location` (`PermissionName.WRITE_ITEM`, `FEDERATION_HEAD_MODE` guard, strict `owner_id` check)
- [x] 2.2 Add SQL-paginated `location` filter to `GET /api/items`, `SearchService`, and owner-scoped `locations` facet in `GET /api/stats/facets`
- [x] 2.3 Emit owner-authorized `iqoqo:physicalLocation` / `schema:location` in `app/core/rdf_service.py` and document new params/endpoints in `app/api/docs.py` (OpenAPI 3.1)

## 3. Frontend Editor, Bulk Toolbar, Facets & i18n

- [x] 3.1 Update `Item` TypeScript type (`frontend/types/frbr.ts`) and add structured location input + "Move to Location" folksonomy tag promotion in `TaxonomyEditor` / `EditItemDialog`
- [x] 3.2 Add bulk location assignment action in `BulkAddToolbar` and location facet filter in `SidebarFilters` / `FilterBar`
- [x] 3.3 Add `en.json` and `pl.json` translations

## 4. Tests & Verification

- [x] 4.1 Add Pytest suite (`tests/test_item_location.py`) covering owner-only visibility, bulk ownership 403/400, `FEDERATION_HEAD_MODE`, SQL pagination, and RDF redaction
- [x] 4.2 Add Vitest component tests and Playwright E2E test for assigning, promoting, and filtering by physical location
- [x] 4.3 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, and `IQOQO_AI_MODE=1 make secret-scan`
