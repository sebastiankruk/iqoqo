## Why
Physical media collectors regularly browse flea markets, basement record shops, book fairs, and board game conventions where mobile cellular signal is weak or non-existent. The native mobile app needs an offline read-only cache of the user's collection and wishlist so they can check what they already own (*"Check if I have it"*) without network connectivity, plus deep-link routing for in-app notifications.

## What Changes

- **Offline Collection & Wishlist Snapshot Cache (`frontend/lib/capacitor/offline-cache.ts`):** Persist the authenticated user's TanStack Query collection (`/api/items`) and wishlist (`/api/wishlist`) read-only snapshots in local IndexedDB / Capacitor storage whenever online, and hydrate from the local cache when `navigator.onLine === false` or network requests time out.
- **Offline Status Banner & Local *"Check if I have it"* Lookup:** Display a subtle `"Offline Mode — Viewing Cached Library (Last synced: ...)"` banner when offline, and allow `/collection` search and barcode *"Check if I have it"* checks to match against cached ISBN/UPC/title records.
- **Notification Center Mobile Deep-Linking:** Ensure tapping any notification in `notification-center.tsx` or incoming `iqoqo://` notification link routes cleanly via `navigation.ts` to the target entity (`/item/[id]`, `/manifestation/[id]`, `/profile?tab=incoming#friends`).

## Capabilities

### New Capabilities
- `mobile-offline-cache-and-deeplinks`: Read-only offline collection/wishlist caching in Capacitor for zero-signal environments and Notification Center deep-link routing.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/lib/capacitor/offline-cache.ts`, `frontend/lib/capacitor/navigation.ts`
- `frontend/components/providers.tsx`, `frontend/app/collection/page.tsx`
- `frontend/components/dashboard/notification-center.tsx`
- `frontend/__tests__/lib/capacitor/offline-cache.test.ts`
