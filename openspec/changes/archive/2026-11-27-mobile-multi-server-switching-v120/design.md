## Context

`frontend/lib/capacitor/storage.ts` currently stores a single `INSTANCE_URL_KEY`, `INSTANCE_NAME_KEY`, and `AUTH_TOKEN_KEY`, while `frontend/lib/capacitor/offline-cache.ts` uses fixed keys (`iqoqo_offline_collection_snapshot`, `iqoqo_offline_wishlist_snapshot`, `iqoqo_offline_profile_snapshot`, `iqoqo_offline_manual_queue`). Switching servers in `ServerSelector` overwrites the URL and calls `removeAuthToken()` + `clearOfflineCache()`.

## Goals / Non-Goals

- **Goals:**
  - Support saving, naming, switching, and removing multiple iqoqo server profiles in Capacitor `Preferences` + `localStorage` mirror.
  - Keep per-server auth tokens isolated in `SecureStoragePlugin` (`iqoqo_auth_token_<serverId>`) and per-server offline snapshots isolated in `offline-cache.ts`.
  - Automatically migrate legacy single-server installations (`iqoqo_instance_url` / `iqoqo_auth_token`) into the first `ServerProfile` on load with zero data loss.
  - Keep `ServerProfile` extensible (`localUrl?: string` reserved for `v1.3.0` `C159` HASS-style local mode).
- **Non-Goals:**
  - Local network / SSID auto-switching (`localUrl` vs `externalUrl`) — deferred to `v1.3.0` (`C159`).
  - Simultaneous multi-server federated search aggregation in the mobile UI.

## Decisions

- **Data Model (`ServerProfile`):**
  - Store `iqoqo_servers_v1` as JSON array of `{ id: string; name: string; url: string; localUrl?: string; addedAt: string; lastUsedAt?: string }` and `iqoqo_active_server_id` in `Preferences` + `localStorage`.
  - `id` is a deterministic slug/UUID generated once on server creation.
- **Credential & Cache Isolation:**
  - `getAuthToken(serverId?)` / `setAuthToken(token, serverId?)` / `removeAuthToken(serverId?)` default to the active server ID and key `SecureStoragePlugin` with `iqoqo_auth_token_${serverId}`.
  - `offline-cache.ts` helper `scopedCacheKey(baseKey, serverId)` namespaces all 4 snapshot/queue keys per active `serverId`.
- **Switch Semantics:**
  - Switching active server updates `iqoqo_active_server_id`, refreshes `inMemoryInstanceUrl`, clears TanStack Query in-memory cache (`queryClient.clear()`), and routes to `/collection` (or `/login` if the target server has no saved token) without deleting the previous server's token or offline cache.

## Risks / Trade-offs

- **Legacy upgrade edge case:** Users upgrading from `v1.0.x`/`v1.1.x` must seamlessly retain their existing session and offline cache; handled by a one-time idempotent `migrateLegacyServerStorage()` run during initialization.
