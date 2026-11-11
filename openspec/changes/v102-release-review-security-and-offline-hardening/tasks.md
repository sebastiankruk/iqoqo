## 1. Backend Federation Head Guard & ConfigService Hardening (`C-01`, `M-05`)

- [x] 1.1 **`C-01` (`app/api/items.py`)**: Enforce `reject_if_federation_head_item_write()` in `add_item_by_manifestation()` (`POST /api/manifestations/<id>/add`) and `add_item()` (`POST /api/item/<isbn>`) when `collection_status != "wish_list"`, and permit `collection_status == "wish_list"` in `add_items_bulk()` (`POST /api/items/bulk`) and `create_item()` (`POST /api/items`). Verify with regression tests in `tests/test_federation_head_mode.py`.
- [x] 1.2 **`M-05` (`app/core/config_service.py`)**: Tighten `is_credential_or_sensitive_key()` to match `is_sensitive_key(key)`, `SENSITIVE_SETTING_KEYS`, or `key.upper().endswith(("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_CLIENT_ID"))` instead of substring matching on `"_ID"`, `"_URL"`, and `"_DATA"`. Verify with unit tests in `tests/test_config_service.py`.

## 2. Shell Script & Makefile Security Hardening (`C-02`, `M-04`)

- [x] 2.1 **`C-02` (`scripts/clone.sh`)**: Update `get_env_var` and `get_remote_env_var` to strip only outer matching quotes (preserving inner password characters), validate `SRC_POSTGRES_USER`, `SRC_POSTGRES_DB`, `DST_POSTGRES_USER`, and `DST_POSTGRES_DB` against `^[a-zA-Z0-9_-]+$`, quote remote SSH command arguments, and pass `DST_POSTGRES_PASSWORD` via `psql -v pw="$DST_POSTGRES_PASSWORD"` (`WITH PASSWORD :'pw'`). Verify with `make lint` / `shellcheck`.
- [x] 2.2 **`M-04` (`Makefile` & `scripts/install.sh`)**: Apply sticky-bit / restricted permissions (`chmod 1777 data/keys` or `chmod 755 data/keys`) after `chmod -R a+rwX` in `ensure-mount-perms`, `preview-up`, and `scripts/install.sh` so unprivileged local processes cannot unlink `data/keys/server.pem`. Verify with `make lint`.

## 3. Frontend Offline Cache Integrity, Queue Mutex & Ownership i18n (`M-01`, `M-02`, `M-03`, `M-06`)

- [x] 3.1 **`M-01` & `M-02` (`frontend/app/collection/page.tsx` & `frontend/lib/api/hooks/wishlist.ts`)**: Move `saveCollectionSnapshot(liveItems)` out of `useMemo` into a dedicated `useEffect` gated on unfiltered personal items (`viewMode === "items" && !effectiveOffline && !appliedQuery && !searchQuery && activeFilters.length === 0 && !missingCoverOnly && !missingIdOnly && (currentScope === "personal" || !currentScope)`), and invoke `saveWishlistSnapshot()` when online wishlist items load. Verify with Vitest unit tests.
- [x] 3.2 **`M-03` (`frontend/app/scan/page.tsx` & `frontend/lib/capacitor/offline-cache.ts`)**: Update `ScanPage.handleManualSubmit` `onError` to only call `enqueueOfflineManualEntry(payload)` on genuine offline/network failures (`!navigator.onLine` or Axios error without `err.response`) while displaying `toast.error` on HTTP `4xx`/`5xx` responses; add an in-flight mutex (`activeFlushPromise`) to `flushOfflineManualQueue()`; and prune synced negative-ID provisional items (`item.id === -entry.timestamp`) from `OFFLINE_COLLECTION_CACHE_KEY`. Verify with unit tests in `frontend/__tests__/lib/capacitor/offline-cache.test.ts` and `frontend/__tests__/app/scan/page.test.tsx`.
- [x] 3.3 **`M-06` (`frontend/components/admin/ownership-management.tsx`, `frontend/app/admin/ownership/page.tsx`, `frontend/components/item/sidebar/sidebar-actions.tsx`)**: Wire `useTranslations("AdminOwnership")` and `useTranslations("ItemDetail")` (`t("reassignOwner")`) to replace hardcoded English strings. Verify with `frontend/__tests__/components/admin/ownership-management.test.tsx` and `frontend/__tests__/components/item/sidebar/sidebar-actions.test.tsx`.

## 4. Verification Gate

- [x] 4.1 Run `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and `IQOQO_AI_MODE=1 make test-parallel` and verify all suites pass.
