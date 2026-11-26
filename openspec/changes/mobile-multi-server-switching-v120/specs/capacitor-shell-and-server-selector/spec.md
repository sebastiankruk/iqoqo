## MODIFIED Requirements

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
