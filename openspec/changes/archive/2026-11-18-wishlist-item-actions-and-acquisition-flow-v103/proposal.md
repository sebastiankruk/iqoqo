## Why

After the `wishlist-api-separation` refactoring moved wishlist entries out of physical `Item` rows (`collection_status="wish_list"`, negative virtual IDs) and into `UserWorkIntent` records served by `/api/wishlist` with positive IDs, users reported that **"there is no way to change items on the wishlist - remove or add"** (`.context/notes/iqoqo development notes.md`, `#bugs #unscheduled #v103`).

A full-stack UX and API audit (`C121`) identified six interconnected defects:

1. **Broken `/manifestation/[id]` Wishlist Actions & 404 Dead Link:** `get_manifestation_detail` (`app/api/manifestations.py:368-371`) still returns a legacy negative `wishlist_item_id = -intent.id`. When an item is on the wishlist, `AddToCollectionDropdown` (`frontend/components/collection/add-to-collection-dropdown.tsx:131-148`) hides `"Add to Wishlist"` and renders `"View Wishlist Item"` pointing to `/item/-<intent.id>`, which now returns **HTTP 404**, and provides **no `"Remove from Wishlist"` action**.
2. **Touch-Invisible & Missing `WishlistCard` Controls:** In `WishlistCard` (`frontend/components/collection/wishlist-card.tsx`), the remove button (`HeartOff`) uses `opacity-0 group-hover:opacity-100` (invisible on mobile/Capacitor touch devices), is completely missing from `variant="horizontal"` (used on Dashboard `CurrentContext`), lacks a quick `"Move to Library / Acquire"` action, and links work-only intents (`manifestation_id == null`) to `/wishlist` (a self-link no-op) instead of `/work/${item.work_id}`.
3. **`/wishlist` Page Lacks Add CTA, Search & Filters:** `frontend/app/wishlist/page.tsx` renders only a static title and grid with no `"+ Add to Wishlist"` CTA (to open `/scan?policy=wishlist`), no empty-state action buttons, and no search/category/sort controls even though `GET /api/wishlist` already supports `?q=`, `?category=`, and `?sort=`.
4. **Acquiring an Item Leaves a Ghost Wishlist Entry:** Creating a physical `Item` via `"Add to My Library"` (`POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>`, `POST /api/items`), Scanner inventory mode (`POST /api/scan`), Bulk Add (`POST /api/items/bulk`), or Manual Entry (`POST /api/items/manual`) does not auto-fulfill (delete) the user's existing `UserWorkIntent` for that `work_id`, leaving acquired items stuck on `/wishlist`.
5. **Broken Wishlist Creation in Bulk Add, Manual Entry, Edition Binding & `/work/[id]`:**
   - `add_items_bulk` (`app/api/items.py:1492`) only creates `UserWorkIntent` when `is_federation_head_mode()` is true; on standard instances, bulk-adding `"Want to Read"` creates orphan `Item(collection_status="wish_list")` rows invisible to `GET /api/wishlist`.
   - `add_item_manual` (`app/api/items.py:1572`) and `ScanPage.handleManualSubmit` (`frontend/app/scan/page.tsx:302`) ignore `policy === "wishlist"` and never route `collection_status == "wish_list"` to `UserWorkIntent`.
   - `_add_wishlist_by_manifestation` (`app/api/items.py:1334`) and `_scan_to_wishlist` (`app/api/scanner.py:569`) omit `expression_id` and `manifestation_id` when creating or updating `UserWorkIntent`.
   - `/work/[id]` (`frontend/components/work/work-detail-client.tsx`) has no button to add/remove a conceptual `Work` on the wishlist (`useCreateWishlistItem` has zero production callers).
6. **Stale TanStack Query `["wishlist"]` Cache:** `AddToCollectionDropdown`, `BulkAddToolbar`, `SuccessCard`, and `ScanPage` invalidate `["items"]` and `["stats"]` but never invalidate `["wishlist"]` (`wishlistQueryKeys.all`).

## What Changes

- **Backend Wishlist & Acquisition Consistency (`app/api/manifestations.py`, `app/api/items.py`, `app/api/scanner.py`):**
  - Return positive `wishlist_item_id = intent.id` in `get_manifestation_detail` (`app/api/manifestations.py`).
  - Populate `expression_id=manifestation.expression_id` and `manifestation_id=manifestation.id` in `_add_wishlist_by_manifestation` and `_scan_to_wishlist` (updating `manifestation_id`/`expression_id` if an existing work-level intent had `None`).
  - Route `collection_status == "wish_list"` in `add_items_bulk` and `add_item_manual` to `UserWorkIntent` on all instances (not only `federation_head_mode`), allowing wishlist manual entry even in `FEDERATION_HEAD_MODE`.
  - Auto-fulfill (delete) any matching `UserWorkIntent(user_id=user_id, work_id=work.id)` whenever a user adds a physical copy (`collection_status != "wish_list"`) across `add_item_by_manifestation`, `add_item`, `create_item`, `add_items_bulk`, `add_item_manual`, and `_scan_to_library`.
- **Frontend `/wishlist` Page, `WishlistCard` & Acquisition Flow (`frontend/app/wishlist/page.tsx`, `frontend/components/collection/wishlist-card.tsx`, `frontend/app/scan/page.tsx`):**
  - Upgrade `/wishlist` with a header Primary CTA (`"+ Add to Wishlist"` $\to$ `/scan?policy=wishlist`), search/category/sort bar wired to `useWishlist({ q, category, sort })`, and empty-state CTAs (`Add to Wishlist` + `Browse Catalog`).
  - Support `?policy=wishlist` URL query parameter initialization on `/scan` (`frontend/app/scan/page.tsx`) and pass `collection_status: policy === "wishlist" ? "wish_list" : "available"` in `handleManualSubmit`.
  - Fix `WishlistCard` (`grid` and `horizontal` variants) so work-only items link to `/work/${item.work_id}`, the `"Remove from Wishlist"` button is always accessible on touch devices, and a 1-tap `"Move to Shelf"` (acquire) action converts the wishlist entry into a physical library `Item` (for manifestation-bound entries, or navigates to `/work/${item.work_id}` to pick an edition for work-only entries).
- **Frontend `/manifestation/[id]` & `/work/[id]` Controls (`frontend/components/collection/add-to-collection-dropdown.tsx`, `frontend/components/work/work-detail-client.tsx`):**
  - Replace the broken `/item/-<id>` link in `AddToCollectionDropdown` with `"View Wishlist"` ($\to$ `/wishlist`) and a destructive `"Remove from Wishlist"` action calling `DELETE /api/wishlist/${wishlistItemId}`.
  - Add a work-level `"Add to Wishlist"` / `"On Wishlist (Remove)"` toggle button in `WorkDetailClient` (`/work/[id]`) wired to `useCreateWishlistItem` / `useDeleteWishlistItem`.
  - Invalidate `["wishlist"]` (`wishlistQueryKeys.all`), `["manifestations"]`, `["works"]`, `["items"]`, and `["stats"]` across all wishlist/item add, remove, bulk-add, and scan mutations.

## Capabilities

### New Capabilities

- `wishlist-item-actions-and-acquisition-flow`: End-to-end wishlist addition, removal, search/filtering, edition binding, work-level intent toggling, and auto-fulfillment upon physical library acquisition.

### Modified Capabilities

<!-- Tracked under the new capability for v1.0.3 -->

## Impact

- **Backend:** `app/api/manifestations.py`, `app/api/items.py`, `app/api/scanner.py`
- **Frontend:** `frontend/app/wishlist/page.tsx`, `frontend/components/collection/wishlist-card.tsx`, `frontend/components/collection/add-to-collection-dropdown.tsx`, `frontend/components/collection/bulk-add-toolbar.tsx`, `frontend/components/work/work-detail-client.tsx`, `frontend/app/scan/page.tsx`, `frontend/components/scanner/success-card.tsx`, `frontend/messages/{en,pl}.json`
- **Tests:** `tests/test_wishlist_api.py`, `tests/test_negative_id_removal.py`, `frontend/__tests__/components/collection/wishlist-card.test.tsx`, `frontend/__tests__/components/collection/add-to-collection-dropdown.test.tsx`, `frontend/__tests__/app/wishlist/page.test.tsx`
