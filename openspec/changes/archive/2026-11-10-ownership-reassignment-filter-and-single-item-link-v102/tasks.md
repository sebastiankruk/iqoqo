## 1. Backend Ownership Items Filtering (`app/`)

- [x] 1.1 Extend `get_ownership_source_items` (`GET /api/admin/ownership/items` in `app/api/admin.py`) and its OpenAPI 3.1 schema to accept optional `q`, `collection_status`, `format`, and `item_id` query parameters, filtering at the SQL level using SQLAlchemy 2.0 `select()` and `escape_ilike_term()` before `LIMIT`/`OFFSET`.

## 2. Frontend Filter Bar & Single-Item Deep-Link (`frontend/`)

- [x] 2.1 Update `getOwnershipItems` in `frontend/lib/api/admin.ts` and `OwnershipManagement` in `frontend/components/admin/ownership-management.tsx` to add search (`q`) and `collection_status` filter controls and automatically hydrate `sourceUserId` and `itemId` from URL query parameters (`?sourceUserId=...&itemId=...`).
- [x] 2.2 Add a `"Reassign Owner"` admin/custodian action button on `/item/[id]` (`frontend/app/item/[id]/page.tsx` / `frontend/components/item/item-sidebar.tsx`, gated by `transfer:item` / admin / custodian permission) linking to `/admin/ownership?sourceUserId=${item.owner_id}&itemId=${item.id}`, along with `en.json` and `pl.json` translations.

## 3. Verification & Test Suite

- [x] 3.1 Add backend tests in `tests/test_manifestation_ownership.py` verifying SQL search filtering, wildcard escaping, `item_id` lookup, and pagination counts on `GET /api/admin/ownership/items`.
- [x] 3.2 Add frontend tests in `frontend/__tests__/components/admin/ownership-management.test.tsx` verifying filter inputs and URL query-param pre-selection, and run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`.
