## MODIFIED Requirements

### Requirement: Offline Profile, Collection & Wishlist Cache

The mobile app SHALL cache the authenticated user's profile, full unfiltered personal collection, and wishlist locally when online, preserve authenticated session state on network failures, serve local search, facet filtering, and ISBN/UPC ownership checks from the cache when offline, and purge the cache upon logout or server switch.

#### Scenario: Authenticated profile state preserved while offline

- **GIVEN** the user previously authenticated while online and the device loses network connectivity
- **WHEN** `useProfile()` fails due to network unreachability (no HTTP response)
- **THEN** the app hydrates the cached `UserProfile` snapshot so the Navbar and `/collection` retain the authenticated state instead of showing the user as logged out (clearing the profile only on HTTP `401`/`404` or explicit logout).

#### Scenario: Online filtered searches do not overwrite full offline collection cache

- **GIVEN** the user previously cached their full personal collection of 100 items while online
- **WHEN** the user searches or applies narrowing facet filters while online (returning 2 items) or switches to `global`/`friends` scope
- **THEN** the app MUST NOT overwrite `iqoqo_offline_collection_snapshot` with the filtered subset, preserving the full personal collection snapshot for offline browsing.

#### Scenario: Wishlist snapshot persisted for offline duplicate lookup

- **GIVEN** the user loads their wishlist while online
- **WHEN** the device later goes offline and the user runs *"Check if I have it"* on `/scan`
- **THEN** `findOfflineDuplicate()` matches against both the cached collection and cached wishlist (`iqoqo_offline_wishlist_snapshot`).

#### Scenario: Collector searches and filters collection while offline

- **GIVEN** the user previously loaded their collection while online and the device loses network connectivity
- **WHEN** the user opens `/collection`, types a search query (title, author, or ISBN), or toggles facet filters (category, format, status, tag, genre, publisher, collection)
- **THEN** the app displays the `"Offline Mode"` banner, hydrates `allItems` from the full `offlineSnapshot.items`, filters the cached collection snapshot locally across both search queries and active filters, and purges the snapshot when the user logs out.

### Requirement: Offline Manual Scan Entry Queue & Auto-Sync

The mobile app SHALL enqueue manual scan entries locally only when offline or when a network connectivity error occurs during submission, serialize background queue flushing with an in-flight lock, prune synced provisional entries from the cached collection snapshot, and surface server-side HTTP `4xx`/`5xx` rejections directly to the user without queueing invalid items.

#### Scenario: Collector saves manual entry while offline

- **GIVEN** the device is offline or the backend is unreachable (no HTTP response) during `/scan` manual entry submission
- **WHEN** the user submits `ManualEntryForm`
- **THEN** the app saves the entry into the local offline manual queue (`iqoqo_offline_manual_queue`), appends a provisional item to the cached collection snapshot, displays a confirmation toast indicating the item is queued for sync, and flushes the queue once with an in-flight mutex when the device comes back online while removing the provisional negative-ID item from the cached snapshot.

#### Scenario: Server rejects manual entry with HTTP 4xx while online

- **GIVEN** the device is online and the server responds with HTTP `400`, `403`, or `422` to `POST /api/items/manual`
- **WHEN** `handleManualSubmit` receives the error response
- **THEN** the app displays an error toast and MUST NOT enqueue the rejected payload into `iqoqo_offline_manual_queue`.
