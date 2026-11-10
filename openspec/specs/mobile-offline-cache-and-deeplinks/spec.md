# mobile-offline-cache-and-deeplinks Specification

## Purpose
Provide read-only offline collection and wishlist caching for zero-signal mobile environments and seamless Notification Center deep-linking.

## Requirements

### Requirement: Offline Read-Only Collection & Wishlist Cache

The mobile app SHALL cache the authenticated user's collection and wishlist locally when online, serve read-only search and ISBN/UPC ownership checks from the cache when offline, and purge the cache upon logout or server switch.

#### Scenario: Collector searches collection while offline

- **GIVEN** the user previously loaded their collection while online and the device loses network connectivity
- **WHEN** the user opens `/collection` and searches by title or ISBN
- **THEN** the app displays the `"Offline Mode"` banner, filters the cached collection snapshot locally, and purges the snapshot when the user logs out.

### Requirement: Offline Profile, Collection & Wishlist Cache

The mobile app SHALL cache the authenticated user's profile, collection, and wishlist locally when online, preserve authenticated session state on network failures, serve local search, facet filtering, and ISBN/UPC ownership checks from the cache when offline, and purge the cache upon logout or server switch.

#### Scenario: Authenticated profile state preserved while offline
- **GIVEN** the user previously authenticated while online and the device loses network connectivity
- **WHEN** `useProfile()` fails due to network unreachability (no HTTP response)
- **THEN** the app hydrates the cached `UserProfile` snapshot so the Navbar and `/collection` retain the authenticated state instead of showing the user as logged out (clearing the profile only on HTTP `401`/`404` or explicit logout).

#### Scenario: Collector searches and filters collection while offline
- **GIVEN** the user previously loaded their collection while online and the device loses network connectivity
- **WHEN** the user opens `/collection`, types a search query (title, author, or ISBN), or toggles facet filters (category, format, status, tag, genre, publisher, collection)
- **THEN** the app displays the `"Offline Mode"` banner, hydrates `allItems` from the full `offlineSnapshot.items`, filters the cached collection snapshot locally across both search queries and active filters, and purges the snapshot when the user logs out.

### Requirement: Offline Manual Scan Entry Queue & Auto-Sync

The mobile app SHALL enqueue manual scan entries locally when offline or when a network error occurs during submission, and automatically synchronize queued entries to the backend once connectivity is restored.

#### Scenario: Collector saves manual entry while offline
- **GIVEN** the device is offline or the backend is unreachable during `/scan` manual entry submission
- **WHEN** the user submits `ManualEntryForm`
- **THEN** the app saves the entry into the local offline manual queue (`iqoqo_offline_manual_queue`), appends a provisional item to the cached collection snapshot, displays a confirmation toast indicating the item is queued for sync, and flushes the queue to the backend when the device comes back online.
