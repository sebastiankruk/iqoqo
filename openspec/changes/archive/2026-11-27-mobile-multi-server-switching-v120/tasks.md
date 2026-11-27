## 1. Multi-Server Storage & Cache Isolation (`frontend/lib/capacitor/`)

- [x] 1.1 Define `ServerProfile` (`id`, `name`, `url`, `localUrl?`, `addedAt`, `lastUsedAt?`) and multi-server registry (`iqoqo_servers_v1`, `iqoqo_active_server_id`) in `frontend/lib/capacitor/storage.ts`, including one-time idempotent migration from legacy `iqoqo_instance_url` / `iqoqo_auth_token`
- [x] 1.2 Namespace `SecureStoragePlugin` auth tokens by `serverId` (`getAuthToken`, `setAuthToken`, `removeAuthToken`) so switching servers preserves tokens for inactive servers
- [x] 1.3 Namespace `frontend/lib/capacitor/offline-cache.ts` keys (`collection`, `wishlist`, `profile`, `manual_queue`) per `serverId` and expose server-scoped clear helpers

## 2. Mobile Server Switcher UI & Connected Indicator

- [x] 2.1 Upgrade `ServerSelector` (`frontend/components/mobile/server-selector.tsx`) to list saved servers, switch active server (clearing TanStack Query in-memory cache only), add/rename servers, and remove servers with confirmation
- [x] 2.2 Update mobile connected-server footer/header indicator to open quick server switcher when running in Capacitor native mode
- [x] 2.3 Add i18n keys in `frontend/messages/en.json` and `frontend/messages/pl.json`

## 3. Tests & Verification

- [x] 3.1 Add Vitest unit tests for `storage.ts` legacy migration, multi-server CRUD, token isolation, and `offline-cache.ts` namespacing
- [x] 3.2 Add Vitest component tests for `ServerSelector` multi-server switching and removal
- [x] 3.3 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, and `IQOQO_AI_MODE=1 make secret-scan`
