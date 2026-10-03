## Context

See `proposal.md` for problem motivation and scope.

Currently in iqoqo:
- Wishlist entries are represented in the database by `UserWorkIntent` (`app/db/core.py`), but only reference `work_id` (F1).
- `/api/items` intercepts queries containing `statuses=wish_list` and synthesizes virtual items by querying `UserWorkIntent` and assigning negative identifiers (`id = -intent.id`).
- `app/core/item_access.py` explicitly branches on negative IDs (`if item_id < 0: intent = db.session.get(UserWorkIntent, -item_id)`), polluting physical item access control.
- `app/api/schemas.py` and frontend UI components contain defensive checks for `id <= 0` or `is_virtual` to suppress physical inventory actions (e.g., QR printing, custody tracking, shelf placement).
- Users cannot express intent for specific translations/media (F2 Expressions) or specific physical releases, F15 Complex Work parts, or F16 Container Works (F3 Manifestations).

## Goals / Non-Goals

**Goals:**
- Provide a dedicated `/api/wishlist` REST blueprint implementing complete CRUD for `UserWorkIntent` using native positive integer IDs.
- Remove all negative-ID synthesis, queries, and mutation branches from `/api/items`, `app/core/item_access.py`, and validation schemas.
- Add optional `expression_id` and `manifestation_id` foreign keys to `UserWorkIntent` to support granular desires for specific editions, translations, F15 Complex Work parts, and F16 Container Works with hierarchy integrity checks.
- Create a linear Alembic migration adding the new columns, foreign keys, and indexes to `user_work_intents`.
- Establish dedicated frontend types (`WishlistItem`), API client functions, and React Query hooks (`useWishlist`, `useCreateWishlistItem`, `useUpdateWishlistItem`, `useDeleteWishlistItem`).
- Separate frontend wishlist views from physical shelf inventory views, removing negative-ID branching from UI components.

**Non-Goals:**
- Altering the physical `Item` (F4) table schema.
- Changing FRBR core hierarchy (Work → Expression → Manifestation → Item).
- Deprecating the convenience endpoint `/works/<id>/intent` (which will continue to function as a work-level intent shortcut).

## Decisions

### 1. Dedicated `/api/wishlist` Blueprint and REST Surface
- **Choice**: Register a new Flask Blueprint `wishlist_bp` mounted at `/api/wishlist` handling:
  - `GET /api/wishlist`: List the authenticated user's wishlist entries with filtering (`status`, `work_type`, `medium_type`, search `q`) and pagination.
  - `POST /api/wishlist`: Create a new wishlist entry (`work_id`, optional `expression_id`, optional `manifestation_id`, `status`, `is_hidden`).
  - `GET /api/wishlist/<int:intent_id>`: Retrieve detail of a single wishlist entry.
  - `PUT /api/wishlist/<int:intent_id>` / `PATCH /api/wishlist/<int:intent_id>`: Update status, visibility, or bound expression/manifestation.
  - `DELETE /api/wishlist/<int:intent_id>`: Remove an entry from the wishlist.
- **Rationale**: Isolates the wishlist domain into its own service boundary, provides clean RESTful semantics, eliminates negative IDs, and simplifies frontend caching and state invalidation.
- **Alternatives Considered**: Retaining `/api/items?is_virtual=true`. Rejected because virtual wishlist desires are not physical items (FRBR F4), violating the core domain model.

### 2. Relational Schema Extension for Expression and Manifestation Binding
- **Choice**: Add nullable foreign keys to `UserWorkIntent` in `app/db/core.py`:
  - `expression_id`: `db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id", ondelete="SET NULL"), nullable=True, index=True)`
  - `manifestation_id`: `db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="SET NULL"), nullable=True, index=True)`
  - Composite unique constraint: `UniqueConstraint("user_id", "work_id", "expression_id", "manifestation_id", name="uq_user_work_intent_target")` (or partial indexes accommodating NULLs).
  - Validation: During creation and update, validate that if `manifestation_id` is supplied, it belongs to `expression_id` (if supplied) and `work_id`. If `expression_id` is supplied, it belongs to `work_id`.
- **Rationale**: Enables users to desire specific translations, audio expressions, or specific physical manifestations (such as board game container boxes [F16] or anthology box-set parts [F15]) while falling back gracefully to Work-level desire if specific editions are deleted.
- **Alternatives Considered**: Creating separate tables `user_expression_intents` and `user_manifestation_intents`. Rejected because it fragments intent queries and duplicates status tracking logic.

### 3. Complete Elimination of Negative IDs
- **Choice**:
  - Remove `_query_virtual_items()` from `app/api/items.py`. Querying `/api/items` returns only concrete physical records from `Item`.
  - Remove `if item_id < 0` branching from `app/api/items.py` (`get_item`, `update_item`, `delete_item`, `add_to_collection_route`).
  - Remove negative ID interception in `app/core/item_access.py` (`get_accessible_item`, `get_item_or_404`). Passing an ID `<= 0` will fail validation or return 404.
  - Update `app/api/schemas.py` to require `id > 0` for Item operations.
- **Rationale**: Eliminates fragile negative-number routing hacks, avoids signed integer arithmetic pitfalls, and ensures `/api/items` is strictly an inventory endpoint.
- **Alternatives Considered**: Keeping a deprecation redirect from `/api/items/-<id>` to `/api/wishlist/<id>`. Rejected as unneeded complexity since both backend and frontend are internal to the iqoqo repository.

### 4. Frontend Type and Component Separation
- **Choice**:
  - Introduce `WishlistItem` interface in `frontend/types/frbr.ts` containing `id`, `user_id`, `work_id`, `expression_id`, `manifestation_id`, `status`, `work`, `expression`, `manifestation`, and timestamps.
  - Create dedicated hooks in `frontend/lib/api/wishlist.ts`: `useWishlist`, `useCreateWishlistItem`, `useUpdateWishlistItem`, `useDeleteWishlistItem`.
  - Separate wishlist rendering from inventory cards: remove `is_virtual = item.id < 0` checks from `ItemCard`, `ItemSidebar`, and collection filters.
  - Dedicated wishlist UI route/view displaying edition badges, status selectors, and fulfillment actions without physical inventory controls (QR codes, lending tracking, shelf location).
- **Rationale**: Clean UI code with zero conditional branching for virtual vs physical items, providing distinct UX tailored to shopping/reading goals vs physical shelf management.
- **Alternatives Considered**: Reusing `ItemCard` with an `isWishlist` boolean prop. Rejected because wishlist items lack item-level inventory concerns (custody, loan requests, conditions) and have different actions (edition selection, fulfill to shelf).

## Risks / Trade-offs

- **[Breaking change for API consumers]** → All frontend calls and backend tests referencing negative item IDs are updated atomically as part of this change.
- **[Orphaned intent targets on manifestation deletion]** → Foreign keys use `ON DELETE SET NULL` so that if a specific manifestation is deleted from the catalog, the user's wishlist entry gracefully reverts to the parent expression or work rather than vanishing.
- **[Database migration on active database]** → Adding nullable columns with foreign keys and indexes to `user_work_intents` is non-blocking and executes in milliseconds on PostgreSQL.

## Migration Plan

1. **Alembic Migration**: Generate and apply migration adding `expression_id` and `manifestation_id` to `inventory.user_work_intents` with foreign keys and indexes.
2. **Backend Deployment**: Deploy `app/api/wishlist.py`, update `app/db/core.py`, and remove negative-ID logic from `app/api/items.py` and `app/core/item_access.py`.
3. **Frontend Deployment**: Deploy new `WishlistItem` types, API client hooks, and decoupled views.
4. **Rollback Strategy**: Reversible migration downgrades the schema by dropping the new columns, while git revert restores previous endpoints if critical regressions occur.
