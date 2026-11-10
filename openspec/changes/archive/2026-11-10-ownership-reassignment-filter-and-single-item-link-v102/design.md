## Context

See `proposal.md` for motivation. In `v0.8.3` (`C59`) and `v0.8.4` (`C69`), we introduced `/admin/ownership` (`OwnershipManagement` in `frontend/components/admin/ownership-management.tsx` and `GET /api/admin/ownership/items` in `app/api/admin.py`). Currently, `get_ownership_source_items` only filters by `Item.owner_id == source_uuid` with `page` and `limit`, making it tedious to locate a single item in a 500+ item catalog.

## Goals / Non-Goals

**Goals:**
- Add SQL-level search (`q`), `collection_status`, `format`, and `item_id` filtering to `GET /api/admin/ownership/items` using `escape_ilike_term()` (from `C100e`) and SQLAlchemy 2.0 `select()`.
- Add a clean search input and status filter bar in `OwnershipManagement`, plus automatic hydration from `?sourceUserId=...&itemId=...` URL search parameters.
- Expose a `"Reassign Owner"` link on `/item/[id]` (inside the existing custodian/admin action cluster so button density stays within `iqoqo-ux-auditor` limits) when the viewer holds `transfer:item` permission.

**Non-Goals:**
- Changing the atomic ownership preview/execution contract (`POST /api/admin/ownership/preview` and `POST /api/admin/ownership/reassign`).

## Decisions

### 1. SQL-Level Filtering with Wildcard Escaping (`escape_ilike_term`)
* **Decision:** Join `Item` $\to$ `Manifestation` $\to$ `Expression` $\to$ `Work` in `get_ownership_source_items` when `q` or `format` is supplied, matching `Work.title`, `Manifestation.isbn13`, `Manifestation.ean`, `Manifestation.upc`, or `Item.local_barcode` via `ILIKE` with `escape_ilike_term(q)` and `escape="\\"`.
* **Rationale (Security & SRE):** Satisfies the global SQL Pagination & Memory Bounds rule (zero in-memory Python list filtering) and prevents `ILIKE` wildcard DoS/enumeration.

### 2. Query-Param Deep-Link Hydration (`?sourceUserId=&itemId=`)
* **Decision:** Read `useSearchParams()` in `OwnershipManagement`. When `sourceUserId` and `itemId` are present on mount, set `sourceUserId`, pass `item_id` (or pre-fill search) to `getOwnershipItems`, and initialize `selectedItemIds = [Number(itemId)]`.
* **Rationale (UX):** Reduces single-item ownership migration from 6+ clicks and manual paging down to 2 clicks (`Reassign Owner` on `/item/[id]` $\to$ choose target user & confirm preview).

## Risks / Trade-offs

- **[Risk] Item `owner_id` missing on public item payload** $\to$ **Mitigation:** Ensure `owner_id` is available on the authenticated `/api/items/<id>` response (already returned for owners/admins/custodians) before rendering the `"Reassign Owner"` deep-link.
