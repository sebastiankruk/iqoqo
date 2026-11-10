## 1. Offline Collection/Wishlist Cache & Notification Deep-Links (`frontend/`)

- [x] 1.1 Implement `frontend/lib/capacitor/offline-cache.ts` to persist and read collection/wishlist snapshots, and purge cached snapshots inside `clearAuthToken()` / `clearAllData()`.
- [x] 1.2 Wire offline fallback hydration and the `"Offline Mode — Viewing Cached Library"` banner into `frontend/app/collection/page.tsx` and `/scan` duplicate checks.
- [x] 1.3 Extend `frontend/lib/capacitor/navigation.ts` and `notification-center.tsx` so notification deep-links resolve cleanly on native mobile without URL rewrites.
- [x] 1.4 Add `en.json` and `pl.json` (sentence-case Polish) translations for offline mode indicators.

## 2. Verification & Tests

- [x] 2.1 Author unit tests in `frontend/__tests__/lib/capacitor/offline-cache.test.ts` verifying snapshot persistence, offline query fallback, and cache purge on logout.
- [x] 2.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
