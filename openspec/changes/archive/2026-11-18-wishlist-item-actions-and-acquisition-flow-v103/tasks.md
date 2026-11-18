## 1. Backend Wishlist & Acquisition Lifecycle (`app/api/manifestations.py`, `app/api/items.py`, `app/api/scanner.py`)

- [x] 1.1 Update `get_manifestation_detail` in `app/api/manifestations.py` so `wishlist_item_id` returns the positive `intent.id` (instead of `-intent.id`).
- [x] 1.2 Update `_add_wishlist_by_manifestation` in `app/api/items.py` and `_scan_to_wishlist` in `app/api/scanner.py` to populate `expression_id=manifestation.expression_id` and `manifestation_id=manifestation.id` when creating `UserWorkIntent` (and backfill them if an existing intent for `(user_id, work.id)` has `manifestation_id is None`).
- [x] 1.3 Add `_fulfill_wishlist_intent_for_manifestation(user_id, manifestation)` in `app/api/items.py` and invoke it whenever a physical `Item` (`collection_status != "wish_list"`) is created in `add_item_by_manifestation`, `add_item`, `create_item`, `add_items_bulk`, `add_item_manual`, and `_scan_to_library` (`app/api/scanner.py`).
- [x] 1.4 Route `collection_status == "wish_list"` in `add_items_bulk` (`app/api/items.py`) and `add_item_manual` (`app/api/items.py`) to `UserWorkIntent` on all instances (not only `is_federation_head_mode()`), and allow `add_item_manual` with `collection_status == "wish_list"` under `FEDERATION_HEAD_MODE`.

## 2. Frontend Wishlist Card, `/wishlist` Page, `/manifestation/[id]`, `/work/[id]` & Scanner (`frontend/`)

- [x] 2.1 Update `AddToCollectionDropdown` (`frontend/components/collection/add-to-collection-dropdown.tsx`) to replace the broken `/item/-<id>` link with `"View Wishlist"` ($\to$ `/wishlist`) and a `"Remove from Wishlist"` button (`DELETE /api/wishlist/${Math.abs(wishlistItemId)}`), and invalidate `["wishlist"]` on both add and remove.
- [x] 2.2 Update `WishlistCard` (`frontend/components/collection/wishlist-card.tsx`) in both `grid` and `horizontal` variants so work-only items link to `/work/${item.work_id}`, the `"Remove from Wishlist"` button is touch-visible without hover, and a `"Move to Shelf"` (acquire) button shelves the manifestation (or navigates to `/work/${item.work_id}` if work-only) and invalidates `["wishlist"]`, `["items"]`, `["stats"]`, and `["manifestations"]`.
- [x] 2.3 Upgrade `WishlistPage` (`frontend/app/wishlist/page.tsx`) with a header Primary CTA (`"+ Add to Wishlist"` $\to$ `/scan?policy=wishlist`), search/category/sort filter controls wired to `useWishlist({ q, category, sort })`, and empty-state CTAs.
- [x] 2.4 Update `WorkDetailClient` (`frontend/components/work/work-detail-client.tsx`) to render a work-level `"Add to Wishlist"` / `"On Wishlist (Remove)"` toggle button for authenticated users using `useWishlist` / `useCreateWishlistItem` / `useDeleteWishlistItem`.
- [x] 2.5 Update `ScanPage` (`frontend/app/scan/page.tsx`), `SuccessCard` (`frontend/components/scanner/success-card.tsx`), and `BulkAddToolbar` (`frontend/components/collection/bulk-add-toolbar.tsx`) to initialize scanner `policy` from `?policy=wishlist`, pass `collection_status` in `handleManualSubmit`, and invalidate `["wishlist"]` across all scan/manual/bulk mutations, with EN/PL i18n keys in `frontend/messages/{en,pl}.json`.

## 3. Automated Tests & Verification

- [x] 3.1 Add/update backend pytest tests in `tests/test_wishlist_api.py` and `tests/test_negative_id_removal.py` covering positive `wishlist_item_id`, edition binding (`expression_id`, `manifestation_id`), `add_items_bulk` / `add_item_manual` wishlist routing, and auto-fulfillment of `UserWorkIntent` when adding a physical `Item`.
- [x] 3.2 Add/update frontend Vitest suites for `WishlistCard` (grid + horizontal + acquire + remove + `/work/[id]` fallback link), `AddToCollectionDropdown` (`Remove from Wishlist` + `["wishlist"]` invalidation), and `WishlistPage` (CTA + search/filter controls).
