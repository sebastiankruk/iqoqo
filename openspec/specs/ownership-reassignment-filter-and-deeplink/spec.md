# ownership-reassignment-filter-and-deeplink Specification

## Purpose
Enable administrators and custodians to filter and search physical items by title, identifier, format, or status during ownership reassignment in `/admin/ownership`, and provide a 1-click `"Reassign Owner"` deep-link directly from `/item/[id]` to pre-select that item for transfer.

## Requirements

### Requirement: Filtered & Escaped Source Item Query in Ownership Reassignment API
The `GET /api/admin/ownership/items` endpoint SHALL support optional `q` (search by Work/Manifestation title, ISBN-13, or `Item.local_barcode`), `collection_status`, `format`, and `item_id` query parameters using SQL-level filtering, escaped `ILIKE` wildcards (`escape_ilike_term`), and bounded `LIMIT`/`OFFSET` pagination while enforcing `PermissionName.TRANSFER_ITEM`.

#### Scenario: Custodian filters source account items by title or barcode

- **GIVEN** an authenticated admin or custodian with `transfer:item` permission querying `GET /api/admin/ownership/items?source_user_id=<uuid>&q=Dune`
- **WHEN** the backend executes the query
- **THEN** it escapes `%`, `_`, and `\` wildcards via `escape_ilike_term()`, filters matching items at the SQL query level before `LIMIT`/`OFFSET`, and returns only matching items and updated pagination totals.

#### Scenario: Deep-link lookup with specific `item_id`

- **GIVEN** an authenticated admin or custodian requests `GET /api/admin/ownership/items?source_user_id=<uuid>&item_id=<id>`
- **WHEN** the item belongs to `source_user_id`
- **THEN** the response returns the matching item so it can be immediately selected without manual pagination.

### Requirement: Ownership Management Filter UI & Single-Item Deep-Link from `/item/[id]`
The `/admin/ownership` UI (`OwnershipManagement` and `OwnershipPage`) SHALL provide localized search and status filter controls using `next-intl` (`AdminOwnership`), hydrate `sourceUserId` and `itemId` from URL query parameters, and `/item/[id]` SHALL render a localized `"Reassign Owner"` (`ItemDetail.reassignOwner`) admin action linking to `/admin/ownership?sourceUserId=<owner_id>&itemId=<item_id>` for users with `transfer:item` permission.

#### Scenario: Admin clicks "Reassign Owner" on `/item/[id]`

- **GIVEN** an authenticated admin or custodian viewing `/item/42` owned by user `u-123` in English or Polish locale
- **WHEN** the user clicks the localized `"Reassign Owner"` button
- **THEN** the browser navigates to `/admin/ownership?sourceUserId=u-123&itemId=42`, automatically selects `u-123` as the source account, filters to item `#42`, pre-checks item `#42` for reassignment preview, and renders all headers and filter controls through `AdminOwnership` translations.
