## MODIFIED Requirements

### Requirement: Localized and Tested Admin Federation Dashboard
The Admin Federation Dashboard (`/admin/federation`, `federation-instances.tsx`, `federation-activity.tsx`, and `instance-settings.tsx`) SHALL use `useTranslations("AdminFederation")` for all user-visible labels, provide `aria-label` attributes on icon-only controls, constrain `FEDERATION_DEFAULT_TRUST` strictly to non-privileged trust levels (`untrusted` or `pending`, never `trusted`), expose localized controls for Instance Actor Key provisioning and remote peer key fingerprint inspection, and be covered by Vitest unit tests.

#### Scenario: Admin federation components render localized labels and constrained trust selector

- **WHEN** an administrator views `/admin/federation` or the Federation section of `/admin/settings` in English or Polish
- **THEN** all headings, table columns, filters, key fingerprint controls, and dialogs render localized strings from `AdminFederation` and `FEDERATION_DEFAULT_TRUST` is selected via a constrained dropdown permitting only `untrusted` or `pending`

## ADDED Requirements

### Requirement: Fail-Closed Federation Settings RBAC and Persistence Parity

The admin settings endpoints (`GET /api/v1/admin/settings` and `PUT /api/v1/admin/settings`) SHALL expose all federation configuration keys (`FEDERATION_ENABLED`, `FEDERATION_BASE_URL`, `FEDERATION_AUTO_ACCEPT_FOLLOWS`, and `FEDERATION_DEFAULT_TRUST`) with accurate value and source metadata, fail closed on unknown or unauthorized keys, reject privileged default trust values, and audit-log federation configuration changes.

#### Scenario: Federation settings endpoint returns persisted and default states accurately

- **WHEN** an administrator with `config:federation` permission requests `GET /api/v1/admin/settings?category=federation`
- **THEN** the response includes `FEDERATION_ENABLED`, `FEDERATION_BASE_URL`, `FEDERATION_AUTO_ACCEPT_FOLLOWS` (defaulting to `"false"` when unset), and `FEDERATION_DEFAULT_TRUST` (defaulting to `"untrusted"` when unset) along with each key's authoritative source (`db`, `env`, or `missing`)

#### Scenario: Unknown setting keys, unauthorized categories, and trusted default trust are rejected

- **WHEN** an authenticated admin-panel caller submits `PUT /api/v1/admin/settings` containing an unrecognized setting key, a federation key without `config:federation` permission, or `FEDERATION_DEFAULT_TRUST="trusted"`
- **THEN** unknown keys and unauthorized keys are rejected without database mutation, `FEDERATION_DEFAULT_TRUST="trusted"` returns HTTP `400`, and valid federation setting updates record an audit log entry

### Requirement: Admin Instance Actor Key Provisioning and Peer Fingerprint Pinning

The Admin Federation interface and API SHALL allow authorized administrators to explicitly provision or rotate the local Instance Actor Key via an authenticated `POST` action and inspect verified `SHA256:...` key fingerprints for both the local instance and discovered remote peer instances.

#### Scenario: Administrator provisions local Instance Actor Key from settings

- **WHEN** an administrator with `config:federation` permission invokes `POST /api/v1/admin/federation/key-fingerprint/provision` (or clicks the provision action when unconfigured)
- **THEN** the backend generates and encrypts the instance RSA-2048 keypair, records an audit log entry, and returns the `SHA256:...` fingerprint for display in Federation Settings

#### Scenario: Administrator compares remote peer SHA-256 fingerprint before trusting peer

- **WHEN** an administrator views discovered peers in `/admin/federation`
- **THEN** each peer offering an ActivityPub instance `Application` actor displays its verified `SHA256:...` public key fingerprint so two administrators can verify identity out-of-band before elevating trust to `trusted`
