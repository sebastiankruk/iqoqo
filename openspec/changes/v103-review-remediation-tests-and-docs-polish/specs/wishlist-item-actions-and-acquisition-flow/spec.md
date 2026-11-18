## MODIFIED Requirements

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
