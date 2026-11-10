## Why
Physical media collectors regularly browse flea markets, basement record shops, book fairs, and board game conventions where mobile cellular signal is weak or non-existent. The native mobile app needs an offline cache of the user's profile, collection, and wishlist so they stay authenticated, can filter and search what they already own (*"Check if I have it"*), and can queue manual scan entries without network connectivity, plus deep-link routing for in-app notifications.

## What Changes

- **Offline Profile, Collection & Wishlist Snapshot Cache (`frontend/lib/capacitor/offline-cache.ts`, `frontend/lib/api/hooks/user.ts`):** Persist the authenticated user's `UserProfile` (`/api/profile/`), collection (`/api/items`), and wishlist (`/api/wishlist`) snapshots in local Capacitor Preferences / `localStorage` whenever online, and hydrate from the local cache when `navigator.onLine === false` or network requests fail without an HTTP response (only logging out on `401`/`404`).
- **Offline Status Banner, Local Facet Filtering & *"Check if I have it"* Lookup (`frontend/app/collection/page.tsx`):** Display the `"Offline Mode — Viewing Cached Library (Last synced: ...)"` banner when offline, hydrate `allItems` from the full `offlineSnapshot.items`, and evaluate both live `searchQuery`/`appliedQuery` text and `activeFilters` (category, format, status, tag, genre, publisher, collection) locally alongside barcode *"Check if I have it"* duplicate checks.
- **Offline Manual Entry Queue & Auto-Sync (`frontend/lib/capacitor/offline-cache.ts`, `frontend/app/scan/page.tsx`):** When saving a manual entry on `/scan` while offline or when a network error occurs, persist the manual entry in a local pending queue (`iqoqo_offline_manual_queue`) with optimistic collection snapshot inclusion, and automatically flush queued items to the backend when connectivity returns.
- **Notification Center Mobile Deep-Linking:** Ensure tapping any notification in `notification-center.tsx` or incoming `iqoqo://` notification link routes cleanly via `navigation.ts` to the target entity (`/item/[id]`, `/manifestation/[id]`, `/profile?tab=incoming#friends`).

## Capabilities

### New Capabilities
- `mobile-offline-cache-and-deeplinks`: Offline profile/collection/wishlist caching, local facet filtering, offline manual scan entry queueing with auto-sync, and Notification Center deep-link routing.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/lib/capacitor/offline-cache.ts`, `frontend/lib/capacitor/navigation.ts`
- `frontend/lib/api/hooks/user.ts`, `frontend/components/providers.tsx`
- `frontend/app/collection/page.tsx`, `frontend/app/scan/page.tsx`
- `frontend/components/dashboard/notification-center.tsx`
- `frontend/__tests__/lib/capacitor/offline-cache.test.ts`
