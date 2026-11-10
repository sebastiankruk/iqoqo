## Why

Custodians and administrators using `/admin/ownership` (`OwnershipManagement`) to reassign physical `Item` ownership between accounts currently have to page through an unfiltered list (`page` + `source_user_id` only) with no search or status/format filtering, and there is no direct link from an item's detail page (`/item/[id]`) to migrate that single item's ownership.

## What Changes

- **Filtered Ownership Items Endpoint (`GET /api/admin/ownership/items`):** Extend `get_ownership_source_items` in `app/api/admin.py` with dialect-safe SQL `ILIKE` search (`q` matching Work/Manifestation title, ISBN-13, or `Item.local_barcode` via `escape_ilike_term()`), plus optional `format`, `collection_status`, and `item_id` query parameters while preserving strict SQL `LIMIT`/`OFFSET` pagination and `PermissionName.TRANSFER_ITEM` RBAC checks.
- **Filter Bar & Deep-Link Hydration in `OwnershipManagement` (`frontend/components/admin/ownership-management.tsx`):** Add a debounced search input (`q`), `collection_status` filter, and URL query-parameter hydration (`?sourceUserId=<uuid>&itemId=<id>`) so opening `/admin/ownership` from a deep link automatically selects the source owner, filters/scrolls to the target `Item`, and pre-selects `selectedItemIds = [itemId]`.
- **Single-Item `"Reassign Owner"` Admin Action on `/item/[id]`:** Add a `"Reassign Owner"` action button in the item detail admin/custodian controls (`frontend/app/item/[id]/page.tsx` / `item-sidebar.tsx`) visible only to users with `transfer:item` / admin / custodian permissions that navigates directly to `/admin/ownership?sourceUserId=${item.owner_id}&itemId=${item.id}`.

## Capabilities

### New Capabilities
- `ownership-reassignment-filter-and-deeplink`: Search and status filtering in `/admin/ownership` plus a 1-click `"Reassign Owner"` deep-link from `/item/[id]` for administrators and custodians.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- **Backend:** `app/api/admin.py` (`get_ownership_source_items`), `app/schemas/admin.py` (OpenAPI 3.1 query parameters)
- **Frontend:** `frontend/lib/api/admin.ts` (`getOwnershipItems`), `frontend/components/admin/ownership-management.tsx`, `frontend/app/item/[id]/page.tsx` (or `frontend/components/item/item-sidebar.tsx`), `frontend/messages/en.json`, `frontend/messages/pl.json`
- **Tests:** `tests/test_manifestation_ownership.py`, `frontend/__tests__/components/admin/ownership-management.test.tsx`
