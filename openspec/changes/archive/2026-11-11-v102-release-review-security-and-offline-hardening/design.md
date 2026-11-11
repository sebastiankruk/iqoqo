## Context

See `proposal.md` for motivation and `.context/notes/review/1.0.2/principal-full-release-1.0.2-review.md` for the full five-lens release audit. This change (`C114b`) resolves all 2 Critical (`C-01`–`C-02`) and 6 Moderate (`M-01`–`M-06`) pre-merge findings for `v1.0.2`, while the 5 Low-severity polish items (`L-01`–`L-05`) are scheduled in `v1.0.3` under `C117` (`v102-review-deferrals-installer-and-openapi-polish-v103`).

## Goals / Non-Goals

**Goals:**
- Close every remaining physical `Item` (`F5_Item`) creation vector on `FEDERATION_HEAD_MODE` instances (`POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>`) while permitting `collection_status == "wish_list"` across single and bulk item endpoints (`C-01`).
- Eliminate SQL and shell injection / password corruption in `scripts/clone.sh` (`C-02`) and restrict `data/keys` permissions in `Makefile` and `scripts/install.sh` (`M-04`).
- Ensure offline collection/wishlist caching in `frontend/app/collection/page.tsx`, `frontend/app/scan/page.tsx`, and `frontend/lib/capacitor/offline-cache.ts` never overwrites the full cache with filtered queries (`M-01`), persists wishlist snapshots (`M-02`), only queues offline items on network failures (`M-03`), serializes queue flushes (`M-03`), and cleans up provisional negative-ID items (`M-03`).
- Tighten `is_credential_or_sensitive_key()` in `app/core/config_service.py` (`M-05`) and wire `AdminOwnership` / `ItemDetail.reassignOwner` translations (`M-06`).

**Non-Goals:**
- Implementing `v1.0.3` Low-priority deferrals (`L-01`–`L-05`), which are tracked in `C117`.

## Decisions

### 1. Authoritative Physical Item Write Guard Placement (`C-01`)
* **Decision:**
  - In `add_item_by_manifestation()` (`app/api/items.py:1272-1275`), keep `if payload.collection_status == "wish_list": return _add_wishlist_by_manifestation(user_id, manifestation, payload)` first, and immediately after it call `guard_err = reject_if_federation_head_item_write()` before creating an `Item`.
  - In `add_item()` (`app/api/items.py:1084`), parse `payload` and check `if payload.collection_status != "wish_list":` (or at the start of physical shelving) and return `reject_if_federation_head_item_write()`.
  - In `add_items_bulk()` (`app/api/items.py:1341-1366`) and `create_item()` (`app/api/items.py:1550-1566`), parse `payload` first and enforce `reject_if_federation_head_item_write()` when `payload.collection_status != "wish_list"`.
* **Rationale:** Aligns every item creation route with the `C112` specification: `iqoqo.cc` never creates local physical `Item` (`F5`) records, while Wishlist (`UserWorkIntent` / `wish_list`) operations remain available.

### 2. Parameterized `psql -v` Password Sync & Identifier Validation in `scripts/clone.sh` (`C-02`) + Sticky-Bit `data/keys` (`M-04`)
* **Decision:**
  - Update `get_env_var` and `get_remote_env_var` in `scripts/clone.sh` to strip `\r` and only outer matching `"` or `'` quotes (`sed -e 's/\r$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/"`) instead of `tr -d $'"\'\r'`.
  - Validate `SRC_POSTGRES_USER`, `SRC_POSTGRES_DB`, `DST_POSTGRES_USER`, and `DST_POSTGRES_DB` against `^[a-zA-Z0-9_-]+$`.
  - Synchronize `DST_POSTGRES_PASSWORD` via `psql -v pw="$DST_POSTGRES_PASSWORD" -c "ALTER USER \"$DST_POSTGRES_USER\" WITH PASSWORD :'pw';"`.
  - In `Makefile` (`ensure-mount-perms` and `preview-up`) and `scripts/install.sh`, set `chmod 1777 data/keys` (sticky bit) or `chmod 755 data/keys` after `chmod -R a+rwX` so non-owner processes cannot unlink `server.pem`.
* **Rationale:** `psql`'s `:'pw'` variable interpolation applies libpq's native SQL literal escaping without exposing the password to SQL syntax parsing or shell expansion.

### 3. Offline Snapshot Integrity, Wishlist Persistence & Queue Mutex (`M-01`, `M-02`, `M-03`)
* **Decision:**
  - In `frontend/app/collection/page.tsx`, remove `saveCollectionSnapshot(liveItems)` from `useMemo` and move it into a `useEffect` that runs only when `viewMode === "items" && !effectiveOffline && !appliedQuery && !searchQuery && activeFilters.length === 0 && !missingCoverOnly && !missingIdOnly && (currentScope === "personal" || !currentScope)`. Also add a `useEffect` that calls `saveWishlistSnapshot(wishlistData.items)` when `wishlistData?.items` is loaded online, plus a call inside `useWishlist` in `frontend/lib/api/hooks/wishlist.ts`.
  - In `frontend/app/scan/page.tsx` (`handleManualSubmit`), check `onError(err)`: only enqueue to `enqueueOfflineManualEntry(payload)` when `(typeof navigator !== "undefined" && !navigator.onLine) || (axios.isAxiosError(err) && !err.response)`. Otherwise display `toast.error(...)`.
  - In `frontend/lib/capacitor/offline-cache.ts`, wrap `flushOfflineManualQueue` in an in-flight singleton promise (`let activeFlushPromise: Promise<{ synced: number; failed: number }> | null = null`) and remove synced provisional items (`item.id === -entry.timestamp`) from `OFFLINE_COLLECTION_CACHE_KEY`.

### 4. Scoped Credential Suffix Check (`M-05`) & Ownership i18n Wiring (`M-06`)
* **Decision:**
  - In `app/core/config_service.py`, update `is_credential_or_sensitive_key(key)` to check `key.upper().endswith(("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_CLIENT_ID"))`.
  - In `frontend/components/admin/ownership-management.tsx`, `frontend/app/admin/ownership/page.tsx`, and `frontend/components/item/sidebar/sidebar-actions.tsx`, wire `useTranslations("AdminOwnership")` and `useTranslations("ItemDetail")`.

## Risks / Trade-offs

- **[Risk] Existing unit tests in `ownership-management.test.tsx` or `sidebar-actions.test.tsx` asserting English labels** $\to$ **Mitigation:** `vitest.setup.ts` automatically loads `frontend/messages/en.json`, so `useTranslations("AdminOwnership")` and `useTranslations("ItemDetail")` resolve to the exact same English strings (`"Search title, ISBN, barcode, local barcode..."`, `"Filter by collection status"`, `"Clear Filters"`, `"Reassign Owner"`).
