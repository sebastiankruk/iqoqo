## Purpose
Provide read-only offline collection and wishlist caching for zero-signal mobile environments and seamless Notification Center deep-linking.

## ADDED Requirements

### Requirement: Offline Read-Only Collection & Wishlist Cache

The mobile app SHALL cache the authenticated user's collection and wishlist locally when online, serve read-only search and ISBN/UPC ownership checks from the cache when offline, and purge the cache upon logout or server switch.

#### Scenario: Collector searches collection while offline
- **GIVEN** the user previously loaded their collection while online and the device loses network connectivity
- **WHEN** the user opens `/collection` and searches by title or ISBN
- **THEN** the app displays the `"Offline Mode"` banner, filters the cached collection snapshot locally, and purges the snapshot when the user logs out.
