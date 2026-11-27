## Context

Physical storage location (e.g., `"Study / Bookcase A / Shelf 2"`) is an attribute of the physical copy (`Item`, FRBR `F5_Item`), not the abstract `Work`, `Expression`, or `Manifestation`. Currently collectors encode locations as unstructured `Item.meta["tags"]` strings, polluting subject folksonomies.

## Goals / Non-Goals

- **Goals:**
  - Store `physical_location` strictly on `inventory.items` (`Item.physical_location`, `String(255)`, nullable, indexed) via a single linear Alembic migration (`len(revision) <= 32`).
  - Provide structured location editing on `/item/[id]` (with one-click promotion from existing `loc:` / location-like folksonomy tags) and bulk location assignment via `PATCH /api/items/bulk-location`.
  - Support SQL-paginated `location` filtering in `GET /api/items`, `SearchService`, `/api/stats/facets`, and `/collection`.
  - Emit owner-authorized `iqoqo:physicalLocation` / `schema:location` in Item RDF/JSON-LD while keeping location private from non-owners.
- **Non-Goals:**
  - Modeling hierarchical 3D room/building floorplans or multi-warehouse ERP stock tables.
  - Exposing `physical_location` on `Work`, `Expression`, or `Manifestation` tiers.

## Decisions

- **Schema & Privacy:**
  - Add `physical_location = db.Column(db.String(255), nullable=True, index=True)` to `Item` in `app/db/core.py`.
  - `Item.to_dict()` and `GET /api/items/<id>` include `physical_location` only when `caller_id == item.owner_id` (or admin); non-owners/anonymous callers receive `null` / omitted field so home shelf layouts are never leaked publicly.
- **Bulk Endpoint (`PATCH /api/items/bulk-location`):**
  - Requires `PermissionName.WRITE_ITEM`, rejects `FEDERATION_HEAD_MODE`, verifies `item.owner_id == current_user.id` for every ID (403 on unauthorized IDs), normalizes whitespace, and updates FTS/cache.
- **Faceted Filtering:**
  - `GET /api/stats/facets` returns owner-scoped `locations` facets for authenticated owners; `GET /api/items?location=...` filters strictly via SQL `WHERE` + `LIMIT`/`OFFSET`.

## Risks / Trade-offs

- **Privacy leakage:** Home shelf/room names can reveal personal layout or high-value storage details; mitigated by strict owner-only serialization and RDF emission gating.
