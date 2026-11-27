## Why

Collectors need to record where each physical copy sits (room, bookcase, shelf, storage box), but currently mix ad-hoc location folksonomy tags with subject tags, making physical inventory audits and shelf filtering noisy and unstructured.

Target release: scheduled for **v1.2.0** (`C157`).

## What Changes

- Introduce a first-class physical location attribute/relation strictly on FRBR `Item` (`F5_Item`) in `app/db/core.py` (via linear Alembic migration) and expose it through `GET`/`PATCH /api/items/<id>` and a new bulk location endpoint (`PATCH /api/items/bulk-location`).
- Add a structured Item Location & Relations Editor UI on `/item/[id]` (integrating with `TaxonomyEditor` / `EditItemDialog` and offering one-click promotion of existing location folksonomy tags) plus bulk location assignment in `BulkAddToolbar`.
- Add SQL-paginated `location` filtering to `GET /api/items`, `SearchService`, `/api/stats/facets`, and `/collection` filter controls (`SidebarFilters` / `FilterBar`).
- Emit owner-authorized physical location metadata in Item RDF/JSON-LD (`iqoqo:physicalLocation` / `schema:location`) while keeping private/non-owner location data redacted.

## Capabilities

### New Capabilities

- `physical-item-location-tagging`: Owner-scoped physical location tagging, structured relations editor, bulk assignment, SQL-paginated collection filtering, and privacy-safe RDF/JSON-LD export strictly on FRBR `Item` (`F5_Item`).

### Modified Capabilities

<!-- None -->

## Impact

- Backend: `app/db/core.py`, `alembic/versions/` (single linear migration, `len(revision) <= 32`), `app/api/items.py`, `app/api/stats.py`, `app/api/docs.py`, `app/core/search_service.py`, `app/core/rdf_service.py`
- Frontend: `frontend/types/frbr.ts`, `frontend/components/item/taxonomy-editor.tsx`, `frontend/components/item/edit-item-dialog.tsx`, `frontend/components/collection/bulk-add-toolbar.tsx`, `frontend/components/collection/sidebar-filters.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- Tests: Pytest (`tests/test_item_location.py`), Vitest, Playwright E2E
