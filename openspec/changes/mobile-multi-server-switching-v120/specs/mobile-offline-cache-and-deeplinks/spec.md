## MODIFIED Requirements

### Requirement: Per-Server Offline Cache Namespacing
Offline collection, wishlist, profile snapshots, and manual-entry queues MUST be isolated per saved `serverId` so switching servers never mixes or overwrites cached library data.

#### Scenario: Offline snapshots stay isolated per server
- **WHEN** a user caches collection items on Server A, switches to Server B, and enters offline mode
- **THEN** `/collection` renders only Server B's cached snapshot (or empty offline state if Server B has not been cached) and never displays Server A's items
