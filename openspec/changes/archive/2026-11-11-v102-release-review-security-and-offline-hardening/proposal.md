## Why

The Principal + Gemini Argon release `v1.0.2` audit (PR #416 — `.context/notes/review/1.0.2/principal-full-release-1.0.2-review.md`) identified 2 Critical (`C-01`–`C-02`) and 6 Moderate (`M-01`–`M-06`) findings across the `FEDERATION_HEAD_MODE` physical item write guard, `scripts/clone.sh` SQL/shell password synchronization, mobile offline collection/wishlist snapshot integrity & queue flushing, `Makefile` `data/keys` permissions, `ConfigService` credential key matching, and `AdminOwnership` i18n wiring that must be resolved before merging `release/1.0.2` into `main`.

## What Changes

- **Complete `FEDERATION_HEAD_MODE` Physical Item Write Guard (`C-01` — `app/api/items.py`):** Enforce `reject_if_federation_head_item_write()` on `POST /api/manifestations/<int:manifestation_id>/add` (`add_item_by_manifestation`) and `POST /api/item/<isbn>` (`add_item`) when `collection_status != "wish_list"`, and permit `collection_status == "wish_list"` in `POST /api/items/bulk` (`add_items_bulk`) and `POST /api/items` (`create_item`).
- **Parameterized SQL Password Sync & Identifier Hardening in `scripts/clone.sh` (`C-02`):** Strip only surrounding quotes in `get_env_var` / `get_remote_env_var` (preserving legitimate inner quote characters in passwords), validate PostgreSQL user/database identifiers against `^[a-zA-Z0-9_-]+$`, quote remote SSH command arguments, and pass `DST_POSTGRES_PASSWORD` via `psql -v pw="$DST_POSTGRES_PASSWORD"` using `:'pw'` literal quoting.
- **Unfiltered Offline Collection Snapshot Persistence & Wishlist Cache Wiring (`M-01`, `M-02` — `frontend/app/collection/page.tsx`):** Move `saveCollectionSnapshot(liveItems)` out of `useMemo` into a dedicated `useEffect` that only persists when viewing unfiltered personal items (`viewMode === "items" && !effectiveOffline && !appliedQuery && !searchQuery && activeFilters.length === 0 && !missingCoverOnly && !missingIdOnly && (currentScope === "personal" || !currentScope)`), and invoke `saveWishlistSnapshot()` when online wishlist data loads so `findOfflineDuplicate()` has populated wishlist data.
- **Network-Only Offline Queueing, Flush Mutex & Provisional Item Cleanup (`M-03` — `frontend/app/scan/page.tsx`, `frontend/lib/capacitor/offline-cache.ts`):** Guard `handleManualSubmit` `onError` so `enqueueOfflineManualEntry(payload)` only runs on genuine offline/network failures (`!navigator.onLine` or Axios error without `err.response`) rather than HTTP `4xx`/`5xx` server rejections; protect `flushOfflineManualQueue()` with an in-flight mutex (`activeFlushPromise`) against concurrent `online` / StrictMode double-flushes; and prune synced negative-ID provisional items (`item.id === -entry.timestamp`) from `OFFLINE_COLLECTION_CACHE_KEY` upon sync.
- **Sticky-Bit / Restricted `data/keys` Directory Permissions (`M-04` — `Makefile`, `scripts/install.sh`):** Apply `chmod 1777 data/keys` (or `chmod 755 data/keys`) after `chmod -R a+rwX ... data` in `ensure-mount-perms`, `preview-up`, and `scripts/install.sh` so unprivileged local processes cannot unlink and replace `data/keys/server.pem`.
- **Strict Suffix Matching in `is_credential_or_sensitive_key()` (`M-05` — `app/core/config_service.py`):** Replace the broad `any(suffix in key ...)` substring check (`"_ID"`, `"_URL"`, `"_DATA"`) with `key.upper().endswith(("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_CLIENT_ID"))`.
- **Wire `AdminOwnership` & `ItemDetail.reassignOwner` Translations (`M-06` — `ownership-management.tsx`, `admin/ownership/page.tsx`, `sidebar-actions.tsx`):** Connect `useTranslations("AdminOwnership")` and `useTranslations("ItemDetail")` to replace hardcoded English filter labels, headers, and button text.

## Capabilities

### New Capabilities
<!-- None — refines and hardens v1.0.2 capabilities before release merge -->

### Modified Capabilities
- `federation-head-showcase-mode`: Enforce `reject_if_federation_head_item_write()` across all physical item creation endpoints (`POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>`, `POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk`) while permitting `collection_status == "wish_list"`.
- `mobile-offline-cache-and-deeplinks`: Persist collection snapshots only on unfiltered personal queries, persist wishlist snapshots when online wishlist data loads, guard manual scan offline queueing to network-only errors, serialize queue flushes with an in-flight mutex, and prune provisional negative-ID items after sync.
- `ownership-reassignment-filter-and-deeplink`: Render `/admin/ownership` filter controls, headers, and `/item/[id]` `"Reassign Owner"` button via `next-intl` translation namespaces (`AdminOwnership`, `ItemDetail.reassignOwner`).
- `v101-review-deferrals-and-polish`: Restrict `is_credential_or_sensitive_key()` in `ConfigService` to exact credential suffixes (`_KEY`, `_SECRET`, `_TOKEN`, `_PASSWORD`, `_CLIENT_ID`) plus `SENSITIVE_SETTING_KEYS`.

## Impact

- **Backend:** `app/api/items.py`, `app/core/config_service.py`
- **Frontend:** `frontend/app/collection/page.tsx`, `frontend/app/scan/page.tsx`, `frontend/lib/capacitor/offline-cache.ts`, `frontend/components/admin/ownership-management.tsx`, `frontend/app/admin/ownership/page.tsx`, `frontend/components/item/sidebar/sidebar-actions.tsx`
- **DevOps / Scripts:** `scripts/clone.sh`, `Makefile`, `scripts/install.sh`
- **Tests:** `tests/test_federation_head_mode.py`, `tests/test_config_service.py`, `frontend/__tests__/lib/capacitor/offline-cache.test.ts`, `frontend/__tests__/app/scan/page.test.tsx`, `frontend/__tests__/components/admin/ownership-management.test.tsx`
