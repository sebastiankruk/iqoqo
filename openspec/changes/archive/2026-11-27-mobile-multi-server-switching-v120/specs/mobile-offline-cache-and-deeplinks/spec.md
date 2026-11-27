## ADDED Requirements

### Requirement: Per-Server Offline Cache Namespacing
Offline collection, wishlist, profile snapshots, and manual-entry queues MUST be isolated per saved `serverId` so switching servers never mixes or overwrites cached library data.

#### Scenario: Offline snapshots stay isolated per server
- **WHEN** a user caches collection items on Server A, switches to Server B, and enters offline mode
- **THEN** `/collection` renders only Server B's cached snapshot (or empty offline state if Server B has not been cached) and never displays Server A's items

## MODIFIED Requirements

### Requirement: Offline Read-Only Collection & Wishlist Cache

The mobile app SHALL cache the authenticated user's collection and wishlist locally when online, serve read-only search and ISBN/UPC ownership checks from the cache when offline, and purge the active server's cache upon logout or server removal while preserving sibling server caches across server switches.

#### Scenario: Collector searches collection while offline

- **GIVEN** the user previously loaded their collection while online and the device loses network connectivity
- **WHEN** the user opens `/collection` and searches by title or ISBN
- **THEN** the app displays the `"Offline Mode"` banner, filters the cached collection snapshot locally, and purges the snapshot when the user logs out.

### Requirement: Offline Profile, Collection & Wishlist Cache

The mobile app SHALL cache the authenticated user's profile, full unfiltered personal collection, and wishlist locally when online, preserve authenticated session state on network failures, serve local search, facet filtering, and ISBN/UPC ownership checks from the cache when offline, and purge the active server's cache upon logout or server removal while preserving sibling server caches across server switches.

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
