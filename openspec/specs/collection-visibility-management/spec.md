# collection-visibility-management Specification

## Purpose
Enable collectors to filter their physical library by `Item` visibility tier (`public`, `friends_only`, `private`) using SQL-level pagination and bulk-update visibility across multiple owned `Item`s atomically while preserving FRBR ownership boundaries and cross-user privacy isolation.

## Requirements

### Requirement: SQL-Paginated Collection Visibility Filtering
`GET /api/items` (across both SQLAlchemy and full-text search paths) SHALL accept a `visibility` query parameter (`public`, `friends_only`, `private`, or `hidden` alias) and apply it as a SQL-level filter prior to `LIMIT`/`OFFSET` pagination, while preventing non-owners from querying another user's `private` items.

#### Scenario: Owner filters personal collection by `friends_only` or `private`

- **GIVEN** an authenticated owner with `public`, `friends_only`, and `private` physical items in their personal library
- **WHEN** the owner requests `GET /api/items?visibility=friends_only&page=1&limit=20`
- **THEN** the response MUST return HTTP `200` containing only the owner's `friends_only` items with accurate SQL-computed `meta.total` and `meta.pages`.

#### Scenario: Cross-user scope rejects visibility leak of private items

- **GIVEN** User A owns `private` items and `friends_only` items
- **WHEN** User B (or a friend) requests `GET /api/items?scope=friends&visibility=private` or `GET /api/items?scope=global&visibility=private`
- **THEN** the backend MUST NOT return any of User A's `private` items (returning an empty page for User A's private items).

### Requirement: Owner-Scoped Bulk Item Visibility Mutation
The system SHALL expose `PATCH /api/items/bulk-visibility` requiring `PermissionName.WRITE_ITEM`, enforcing `FEDERATION_HEAD_MODE` guards, validating a bounded non-empty list of `item_ids` and canonical target `visibility` (`public`, `friends_only`, `private`), and updating only items owned by the authenticated caller via `Item.set_visibility()`.

#### Scenario: Owner bulk-updates multiple owned items to `friends_only`

- **GIVEN** an authenticated user who owns items `[101, 102, 103]` currently marked `public`
- **WHEN** the user sends `PATCH /api/items/bulk-visibility` with `{"item_ids": [101, 102, 103], "visibility": "friends_only"}`
- **THEN** all three items MUST persist `visibility == "friends_only"` and `is_hidden == True` atomically, invalidate facet caches, and return HTTP `200` with the updated count.

#### Scenario: Bulk visibility update rejects unowned items or read-only tokens

- **GIVEN** an authenticated user with item `101` (owned) and item `999` (owned by another user), OR authenticating with a read-only Personal Access Token lacking `write:items`
- **WHEN** the caller sends `PATCH /api/items/bulk-visibility`
- **THEN** the backend MUST reject the entire batch with HTTP `403` and MUST NOT modify any item's visibility.

### Requirement: Collection UI Visibility Filter and Bulk Visibility Toolbar
The `/collection` page SHALL provide a Visibility filter in `SidebarFilters` / `FilterBar` synced with URL query params and multi-select item selection in `My Collection` (`items` view) paired with a `"Change Visibility"` action in a floating bulk action toolbar.

#### Scenario: Collector filters by visibility and bulk-changes selected items in `/collection`

- **GIVEN** an authenticated user viewing `/collection` in `items` mode
- **WHEN** the user activates the `Private` visibility filter chip, selects multiple items, and chooses `"Set Visibility -> Friends Only"`
- **THEN** the UI MUST call `PATCH /api/items/bulk-visibility`, update the active filter query parameter in the URL, and refresh the displayed collection and facet counts.
