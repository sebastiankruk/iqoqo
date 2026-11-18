# wishlist-item-actions-and-acquisition-flow Specification

## Purpose
TBD - created by archiving change wishlist-item-actions-and-acquisition-flow-v103. Update Purpose after archive.

## Requirements

### Requirement: Manifestation Detail Exposes Positive Wishlist ID and Removal Action

`GET /api/manifestations/<id>` SHALL return a positive integer `wishlist_item_id` matching the authenticated user's `UserWorkIntent.id` when the manifestation's work is on the user's wishlist, and `AddToCollectionDropdown` SHALL allow the user to remove the item from the wishlist or navigate to `/wishlist` without ever linking to `/item/-<id>`.

#### Scenario: Manifestation detail returns positive wishlist_item_id

- **GIVEN** an authenticated user with a `UserWorkIntent` (`id = 42`) for the work embodied by manifestation `10`
- **WHEN** `GET /api/manifestations/10` is requested
- **THEN** the response `data.wishlist_item_id` MUST equal `42` (a positive integer).

#### Scenario: Manifestation dropdown removes item from wishlist

- **GIVEN** `AddToCollectionDropdown` is rendered with `wishlistItemId={42}`
- **WHEN** the user opens the dropdown and clicks `"Remove from Wishlist"`
- **THEN** the client MUST call `DELETE /api/wishlist/42` and invalidate the `["wishlist"]` and `["manifestations"]` query caches, and MUST NOT render any link to `/item/-42`.

### Requirement: Acquiring a Physical Item Automatically Fulfills Wishlist Intent

Creating a physical `Item` (`collection_status != "wish_list"`) for a manifestation SHALL automatically delete any existing `UserWorkIntent` belonging to the same user and work across `POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>`, `POST /api/items`, `POST /api/items/bulk`, `POST /api/items/manual`, and `POST /api/scan`.

#### Scenario: Adding manifestation to library removes wishlist intent

- **GIVEN** an authenticated user has a `UserWorkIntent` for work `W` embodied by manifestation `M`
- **WHEN** the user calls `POST /api/manifestations/<M>/add` with `{"collection_status": "available"}`
- **THEN** a physical `Item` MUST be created for manifestation `M` AND the user's `UserWorkIntent` for work `W` MUST be deleted from `user_work_intents`.

#### Scenario: Scanning barcode in inventory mode fulfills wishlist intent

- **GIVEN** an authenticated user has a `UserWorkIntent` for work `W` and scans its barcode via `POST /api/scan` with `collection_status="available"`
- **THEN** the physical `Item` MUST be created AND the matching `UserWorkIntent` for work `W` MUST be deleted.

### Requirement: Wishlist Additions Preserve Edition Binding and Route Consistently to UserWorkIntent

Adding an item with `collection_status="wish_list"` via `POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>`, `POST /api/items`, `POST /api/items/bulk`, `POST /api/items/manual`, or `POST /api/scan` SHALL create or update a `UserWorkIntent` (never a physical `Item`) with `work_id`, `expression_id`, and `manifestation_id` populated from the target manifestation, reactivating any existing `"fulfilled"` `UserWorkIntent` row to an active `want_to_*` progress status and upgrading its `expression_id` and `manifestation_id` when a specific manifestation is provided.

#### Scenario: Adding by manifestation binds expression_id and manifestation_id

- **GIVEN** manifestation `M` belongs to expression `E` and work `W`
- **WHEN** an authenticated user posts `{"collection_status": "wish_list"}` to `POST /api/manifestations/<M>/add`
- **THEN** the resulting `UserWorkIntent` MUST have `work_id == W.id`, `expression_id == E.id`, and `manifestation_id == M.id`.

#### Scenario: Bulk add and manual entry with wish_list create UserWorkIntent

- **GIVEN** a standard (non-federation-head) instance
- **WHEN** an authenticated user submits `POST /api/items/bulk` or `POST /api/items/manual` with `collection_status="wish_list"`
- **THEN** the backend MUST create `UserWorkIntent` record(s) visible in `GET /api/wishlist` and MUST NOT create physical `Item` rows.

#### Scenario: Re-wishlisting a work with an existing fulfilled UserWorkIntent reactivates it and binds the target edition

- **GIVEN** an authenticated user has an existing `UserWorkIntent` for work `W` with `status == "fulfilled"` and `manifestation_id == None`
- **WHEN** the user posts `{"collection_status": "wish_list"}` to `POST /api/manifestations/<M>/add` (where manifestation `M` embodies expression `E` of work `W`)
- **THEN** the existing `UserWorkIntent` MUST have its `status` reset to `"want_to_read"` (or the category's default `want_to_*` status), `expression_id` set to `E.id`, and `manifestation_id` set to `M.id`.

### Requirement: WishlistCard Provides Touch-Accessible Acquire and Remove Actions and Valid Links

`WishlistCard` (in both `grid` and `horizontal` variants) SHALL provide touch-accessible `"Move to Shelf"` (acquire) and `"Remove from Wishlist"` controls without requiring mouse hover, and SHALL link work-only wishlist entries (`manifestation_id == null`) to `/work/<work_id>`.

#### Scenario: Work-only wishlist card links to work detail page

- **GIVEN** a `WishlistEntry` with `work_id = 7` and `manifestation_id = null`
- **WHEN** `WishlistCard` renders in `grid` or `horizontal` mode
- **THEN** its primary card link `href` MUST be `/work/7` (not `/wishlist`).

#### Scenario: Removing or acquiring from WishlistCard in grid or horizontal mode

- **GIVEN** a `WishlistEntry` with `id = 15` and `manifestation_id = 99` rendered in `WishlistCard` (`grid` or `horizontal`)
- **WHEN** the user clicks `"Remove from wishlist"`
- **THEN** `DELETE /api/wishlist/15` MUST be called; and **WHEN** the user clicks `"Move to library"`
- **THEN** `POST /api/manifestations/99/add` MUST be called with `collection_status: "available"` and the `["wishlist"]` and `["items"]` caches MUST be invalidated.

### Requirement: Wishlist Page Provides Add CTA, Search, Category Filter, and Sort Controls, and Work Page Supports Wishlist Toggle

The `/wishlist` page SHALL render a primary `"+ Add to Wishlist"` CTA linking to `/scan?policy=wishlist` (which initializes the scanner in `wishlist` policy mode), along with localized search (`q`), category filter (`category`), and sort (`sort`) controls wired to `GET /api/wishlist` (which SHALL escape backslashes via `escape_ilike_term`), and `/work/[id]` SHALL render a button allowing authenticated users to add or remove the conceptual `Work` on their wishlist.

#### Scenario: Wishlist page search and Add CTA

- **GIVEN** an authenticated user visits `/wishlist`
- **WHEN** the page renders
- **THEN** it MUST display an `"+ Add to Wishlist"` link to `/scan?policy=wishlist` and localized search/category/sort controls that pass `q`, `category`, and `sort` parameters to `useWishlist`.

#### Scenario: Toggling wishlist on Work detail page

- **GIVEN** an authenticated user visits `/work/12`
- **WHEN** the user clicks `"Add to Wishlist"` (or `"Remove from Wishlist"` when already on the wishlist)
- **THEN** the client MUST call `POST /api/wishlist` with `{"work_id": 12}` (or `DELETE /api/wishlist/<intent_id>`) and refresh the wishlist state.
