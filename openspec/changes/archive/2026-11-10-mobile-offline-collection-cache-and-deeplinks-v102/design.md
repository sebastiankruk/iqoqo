## Context

Once `v1.0.0` lands the Capacitor apps and `v1.0.1` completes the `#v100` domain expansions, the highest-value mobile capability for physical collectors is offline access to their own catalog and offline manual entry capture when shopping in dead zones.

## Goals / Non-Goals

**Goals:**
- Cache the user's `UserProfile`, personal collection, and wishlist locally on device so the user stays logged in and can run local search, facet filtering, and ISBN/UPC duplicate checks when offline.
- Enqueue manual scan entries locally when offline (`iqoqo_offline_manual_queue`) and automatically flush them to `/api/items/manual` when connectivity returns.
- Clear the offline cache and pending queue immediately upon logout (`clearAllData()`) or server switch so private inventory never leaks across accounts.
- Route notification taps cleanly on mobile.

**Non-Goals:**
- Multi-device CRDT conflict resolution for edits to existing server items.

## Decisions

### Profile, Collection & Wishlist Cache Cleared on Logout
* **Decision:** Store the serialized `UserProfile`, collection, and wishlist snapshots in Capacitor Preferences / `localStorage`, hydrate `useProfile()` from the cached profile when network requests fail without an HTTP status (`!err.response`), and purge all snapshots inside `removeAuthToken()` / `clearAllMobileStorage()`.
* **Rationale:** Prevents transient network drops or airplane mode from logging the user out in the UI and resetting `/collection` view modes, while guaranteeing zero cross-account data leakage on explicit logout or `401`/`404`.

### Client-Side Facet & Live Search Evaluation When Offline
* **Decision:** When `isOffline` is true (or when live item queries fail while a cached snapshot exists), hydrate `allItems` directly from `offlineSnapshot.items` and evaluate live `searchQuery`/`appliedQuery` plus `activeFilters` (status, category, format, tag, genre, publisher, collection) in memory inside `filteredItems`.
* **Rationale:** Online mode delegates filtering to SQL pagination; offline mode must evaluate the same predicates locally over the cached snapshot so filter chips and typing in the search bar work seamlessly without server round-trips.

### Offline Manual Entry Queue with Reconnect Flush
* **Decision:** Persist manual scan submissions made while offline (or failing with a network error) into `iqoqo_offline_manual_queue`, optimistically append a provisional `Item` to `offlineSnapshot`, and flush queued payloads sequentially when the `online` event fires.
* **Rationale:** Allows collectors at flea markets or basement shops to record newly acquired items immediately even when barcode lookup and server connectivity are unavailable.
