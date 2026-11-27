# physical-item-location-tagging Specification

## Purpose
TBD - created by archiving change physical-item-location-tagging-v120. Update Purpose after archive.

## Requirements

### Requirement: FRBR Item-Scoped Physical Location Storage & Privacy
Physical storage locations MUST be stored strictly on FRBR `Item` (`F5_Item`) and MUST only be visible to the item owner (or authorized admin).

#### Scenario: Owner sets and reads item physical location

- **WHEN** an authenticated owner updates `physical_location` on their `Item` via `PATCH /api/items/<id>`
- **THEN** the location is saved on `Item.physical_location`, returned in `GET /api/items/<id>` to the owner, and redacted (`null`) for anonymous or non-owner callers

#### Scenario: Bulk location assignment enforces ownership and Federation Hub guard

- **WHEN** an authenticated user sends `PATCH /api/items/bulk-location` with `{ "item_ids": [...], "physical_location": "Living Room / Shelf 3" }`
- **THEN** the backend verifies `PermissionName.WRITE_ITEM`, `FEDERATION_HEAD_MODE=false`, and ownership of all target items (returning `403` if any item belongs to another user)

### Requirement: SQL-Paginated Location Filtering & Folksonomy Promotion
Collectors MUST be able to filter `/collection` by physical location using SQL-level pagination and promote legacy location tags into `Item.physical_location`.

#### Scenario: Collection filtered by physical location

- **WHEN** the owner selects a location facet in `/collection` (`GET /api/items?location=...`)
- **THEN** only the owner's items matching that `physical_location` are returned using SQL `LIMIT`/`OFFSET` pagination

#### Scenario: Promoting a folksonomy tag to structured location

- **WHEN** the owner clicks "Move to Location" on a tag in the `/item/[id]` `TaxonomyEditor` / relations editor
- **THEN** the tag is removed from `tags` and saved into `Item.physical_location`
