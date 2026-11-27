## ADDED Requirements

### Requirement: Multi-Server Profile Registry & Switching
The mobile Capacitor client MUST allow users to save, switch between, rename, and remove multiple iqoqo server profiles without losing credentials or offline data for inactive servers.

#### Scenario: Switching between two saved servers preserves tokens
- **WHEN** a user has Server A (authenticated) and Server B (authenticated) saved in `ServerSelector` and switches active server from A to B
- **THEN** the active API base URL updates to Server B, requests use Server B's isolated `SecureStoragePlugin` token, and Server A's token remains intact for instant switch-back

#### Scenario: Legacy single-server upgrade migration
- **WHEN** an existing mobile user upgrades from `v1.1.x` with `iqoqo_instance_url` and `iqoqo_auth_token` populated
- **THEN** `storage.ts` automatically migrates the entry into `ServerProfile[0]` and binds the existing token to its `serverId` without requiring re-login

#### Scenario: Removing an inactive or active server
- **WHEN** the user removes a saved server profile
- **THEN** only that server's `SecureStoragePlugin` token and offline cache namespace are deleted; if it was active, the next saved server becomes active (or `ServerSelector` prompts for a new URL if none remain)

## MODIFIED Requirements

### Requirement: Hardware-Encrypted Auth Token Storage on Mobile

The mobile storage layer SHALL store per-server isolated authentication tokens (`iqoqo_auth_token_<serverId>`, falling back to un-scoped `AUTH_TOKEN_KEY` only before migration when no server profile is active) exclusively in hardware-backed encrypted storage (`capacitor-secure-storage-plugin`) and SHALL store multi-server registry and non-sensitive instance metadata (`SERVERS_STORAGE_KEY`, `ACTIVE_SERVER_ID_KEY`, `INSTANCE_URL_KEY`, `INSTANCE_NAME_KEY`) in `@capacitor/preferences`.

#### Scenario: Storing and retrieving auth token on native platform

- **GIVEN** the application is running on iOS or Android (`isNativeApp() === true`)
- **WHEN** `setAuthToken(token)` is called
- **THEN** the token is written via `SecureStoragePlugin.set` and never written to plain-text `Preferences`.
