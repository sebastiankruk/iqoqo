## 1. Database Model & Migration

- [x] 1.1 Update `UserWorkIntent` in `app/db/core.py` to add `expression_id` and `manifestation_id` nullable foreign keys, relationships, and updated unique constraint, verifying syntax and imports with `python3 -c "from app.db.core import UserWorkIntent"`
- [x] 1.2 Create a linear Alembic migration in `migrations/versions/` adding `expression_id` and `manifestation_id` to `inventory.user_work_intents` with foreign keys and indexes, verifying upgrade and downgrade execution on a test database

## 2. Dedicated Wishlist API Blueprint

- [x] 2.1 Create `app/api/wishlist.py` with Flask blueprint `wishlist_bp` implementing `GET /api/wishlist`, `POST /api/wishlist`, `GET /api/wishlist/<id>`, `PUT /api/wishlist/<id>`, and `DELETE /api/wishlist/<id>` with positive IDs and rich FRBR serialization, verifying endpoints with unit tests in `tests/test_api_wishlist.py`
- [x] 2.2 Register `wishlist_bp` in application factory (`app/__init__.py`), verifying endpoint discovery and routing with `pytest tests/test_api_wishlist.py`
- [x] 2.3 Implement FRBR hierarchy validation in `app/api/wishlist.py` ensuring bound `manifestation_id` matches `expression_id` and `work_id` (supporting F15 Complex Works and F16 Container Works), verifying with hierarchy validation test cases

## 3. Removal of Negative-ID Hack from Items API & Access Control

- [x] 3.1 Remove `_query_virtual_items()` and wishlist synthesis from `get_items()` in `app/api/items.py`, ensuring `/api/items` exclusively returns physical `Item` records, verifying with `pytest tests/test_api_items.py`
- [x] 3.2 Remove negative-ID routing and handling from single item endpoints (`get_item`, `update_item`, `delete_item`, `add_to_collection_route`) in `app/api/items.py`, verifying negative IDs return 404 with test assertions
- [x] 3.3 Remove negative-ID resolution from `app/core/item_access.py` (`get_accessible_item`, `get_item_or_404`), verifying positive-only resolution with item access unit tests
- [x] 3.4 Update Pydantic schemas in `app/api/schemas.py` to reject non-positive IDs and remove virtual item bypasses, verifying schema validation tests

## 4. Frontend Types & API Client Integration

- [x] 4.1 Define `WishlistItem` interface and DTO types in `frontend/types/frbr.ts`, verifying types with `npm --prefix frontend run typecheck`
- [x] 4.2 Create `frontend/lib/api/wishlist.ts` with API client methods and React Query hooks (`useWishlist`, `useCreateWishlistItem`, `useUpdateWishlistItem`, `useDeleteWishlistItem`), verifying hook tests
- [x] 4.3 Update catalog and detail action triggers ("Add to Wishlist", "Remove from Wishlist") to dispatch to `/api/wishlist` rather than mutating items via negative IDs, verifying UI interactions in component tests

## 5. Frontend View Separation & Cleanup

- [x] 5.1 Decouple wishlist view from inventory views, removing `item.id < 0` and `collection_status === 'wish_list'` branching from `ItemCard`, `ItemSidebar`, and inventory filters, verifying component render tests
- [x] 5.2 Create or update dedicated Wishlist view and cards rendering edition and media badges without physical inventory actions (no QR codes or shelf placement), verifying with vitest component tests
- [x] 5.3 Update stats cards and counters in `frontend/components/dashboard/` and collection summaries to clearly distinguish between physical inventory count and wishlist intent count, verifying with dashboard tests

## 6. Verification & Regression Testing

- [x] 6.1 Run full backend test suite for items and wishlist via `pytest tests/test_api_items.py tests/test_api_wishlist.py` to ensure zero regressions
- [x] 6.2 Execute full project validation and linting with `IQOQO_AI_MODE=1 make lint` and frontend test suite to verify overall integrity
