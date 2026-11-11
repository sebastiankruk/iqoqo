## 1. Offline Profile/Collection/Wishlist Cache, Queue & Notification Deep-Links (`frontend/`)

- [x] 1.1 Implement `frontend/lib/capacitor/offline-cache.ts` to persist and read collection/wishlist snapshots, and purge cached snapshots inside `clearAuthToken()` / `clearAllData()`.
- [x] 1.2 Wire offline fallback hydration and the `"Offline Mode — Viewing Cached Library"` banner into `frontend/app/collection/page.tsx` and `/scan` duplicate checks.
- [x] 1.3 Extend `frontend/lib/capacitor/navigation.ts` and `notification-center.tsx` so notification deep-links resolve cleanly on native mobile without URL rewrites.
- [x] 1.4 Add `en.json` and `pl.json` (sentence-case Polish) translations for offline mode indicators.
- [x] 1.5 Add `UserProfile` snapshot persistence (`saveProfileSnapshot`, `getCachedProfileSnapshot`) in `frontend/lib/capacitor/offline-cache.ts` and update `useProfile()` in `frontend/lib/api/hooks/user.ts` to fall back to the cached profile on network errors (only logging out on HTTP `401`/`404`).
- [x] 1.6 Update `frontend/app/collection/page.tsx` so offline mode hydrates `allItems` from the full `offlineSnapshot.items` and evaluates both live `searchQuery`/`appliedQuery` and `activeFilters` (category, format, status, tag, genre, publisher, collection) locally with accurate counts.
- [x] 1.7 Implement offline manual scan entry queueing (`enqueueOfflineManualEntry`, `getOfflineManualQueue`, `flushOfflineManualQueue`) in `frontend/lib/capacitor/offline-cache.ts` and wire `handleManualSubmit` + online auto-sync in `frontend/app/scan/page.tsx`.

## 2. Verification & Tests

- [x] 2.1 Author unit tests in `frontend/__tests__/lib/capacitor/offline-cache.test.ts` verifying snapshot persistence, offline query fallback, and cache purge on logout.
- [x] 2.2 Add unit tests covering offline `UserProfile` fallback, offline manual entry queue/flush, and offline collection filtering/search.
- [x] 2.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
