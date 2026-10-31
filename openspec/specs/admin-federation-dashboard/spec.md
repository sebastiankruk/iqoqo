# admin-federation-dashboard Specification

## Purpose
Admin Federation management UI, instance trust settings, activity logs, and full i18n localization.

## Requirements

### Requirement: Admin Federation Instance Management

The admin panel SHALL allow administrators to view, discover, block, and set trust levels for remote Fediverse instances using a 3-category trust model: `trusted`, `untrusted`, and `blocked`.

#### Scenario: Changing instance trust level

- **WHEN** An administrator changes instance trust from `untrusted` to `trusted`
- **THEN** The backend updates `trust_level` to `trusted` and future catalog activities auto-merge empty metadata fields while allowing users who opted into auto-accept to automatically accept follow requests from that peer.

#### Scenario: Peer instance row displays single clear trust selector without redundant pending badge

- **WHEN** an administrator views the Federation Instances list at `/admin/federation`
- **THEN** each peer instance row displays its trust level exclusivamente via the 3-option trust selector (`Trusted`, `Untrusted`, `Blocked`) without rendering a separate `"Pending Review"` status pill next to the selector

### Requirement: Localized and Tested Admin Federation Dashboard

The Admin Federation Dashboard (`/admin/federation`, `federation-instances.tsx`, `federation-activity.tsx`, and `instance-settings.tsx`) SHALL use `useTranslations("AdminFederation")` for all user-visible labels, provide `aria-label` attributes on icon-only controls, remove global `FEDERATION_DEFAULT_TRUST` and `FEDERATION_AUTO_ACCEPT_FOLLOWS` controls from the global Admin Settings UI (`instance-settings.tsx`), expose localized controls for Instance Actor Key provisioning and remote peer key fingerprint inspection, and be covered by Vitest unit tests.

#### Scenario: Admin federation components render localized labels and constrained trust selector

- **WHEN** an administrator views `/admin/federation` or the Federation section of `/admin/settings` in English or Polish
- **THEN** all headings, table columns, filters, key fingerprint controls, and dialogs render localized strings from `AdminFederation`, peer trust selectors expose only `Trusted`, `Untrusted`, and `Blocked`, and global `FEDERATION_DEFAULT_TRUST` / `FEDERATION_AUTO_ACCEPT_FOLLOWS` controls are omitted from Admin Settings in favor of per-user profile consent settings

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

### Requirement: Atomic Admin Settings Mutation, Strict Instance Actor Fingerprint Filtering, and Safe Key Rotation UI

The Admin Settings and Federation Dashboard endpoints and UI SHALL validate the entire `PUT /api/v1/admin/settings` payload (known keys, RBAC permissions, and value constraints) before applying any database mutations in a single atomic transaction with `EntityAuditLog` records, SHALL resolve remote peer `key_fingerprint` values strictly from canonical `/api/federation/actor` actor records (never falling back to remote `Person` user actors), and SHALL treat `"Not configured"` fingerprint responses in `InstanceSettings` as unprovisioned—hiding the Copy button, displaying **"Generate Instance Key"** (`rotate: false`) on initial creation, and requiring explicit confirmation before rotating an existing live Instance Actor Key.

#### Scenario: Multi-key admin settings update rolls back completely when one key is invalid

- **WHEN** an administrator submits `PUT /api/v1/admin/settings` with `{"FEDERATION_ENABLED": "true", "FEDERATION_DEFAULT_TRUST": "trusted"}` (or a valid key paired with an unknown/unauthorized key)
- **THEN** the endpoint returns HTTP `400` or `403` without persisting `FEDERATION_ENABLED="true"` or leaving un-audited partial updates

#### Scenario: Remote user Person actor key is never displayed as peer Instance Actor Key Fingerprint

- **WHEN** a peer instance has cached remote user `Person` actors (`/u/alice` or `/u/actor`) in `FederationActor` but has no `/api/federation/actor` `Application` actor key cached
- **THEN** `GET /api/v1/admin/federation/instances` and `POST /api/v1/admin/federation/instances` return `key_fingerprint: null` for that peer

#### Scenario: Unconfigured Instance Settings renders Generate Instance Key and confirms live rotation

- **WHEN** an administrator opens Federation Settings while `server.pem` is unconfigured (`fingerprint == "Not configured"`), and later clicks **Rotate Key** after a `SHA256:...` fingerprint is active
- **THEN** the unconfigured view hides the Copy button, displays **Generate Instance Key**, and sends `{"rotate": false}`, while clicking **Rotate Key** on an active key prompts for confirmation before rotating `server.pem`

### Requirement: Reciprocal Peering Guidance and Asymmetric Trust Indication

The Admin Federation Dashboard (`/admin/federation` and `federation-instances.tsx`) SHALL explain in simple, plain language how peering works, why adding a peer is a one-way setting on this server, and what each of the 3 trust levels (`Trusted`, `Untrusted`, `Blocked`) controls for friend requests, collection/loan requests, and catalog metadata.

#### Scenario: Admin views federation instances with peering explanation banner

- **WHEN** an administrator views the Federation Instances panel at `/admin/federation`
- **THEN** the interface renders a plain-language callout banner explaining that:
  1. Adding a peer sets how **your** server treats requests and data coming from that peer (the other server's admin must also add your domain on their side),
  2. **Trusted** allows catalog metadata to auto-fill empty fields, allows friend & loan requests, and lets local users optionally auto-accept follow requests from this peer,
  3. **Untrusted** (the default for new peers) still allows users to send/receive friend and loan requests with manual approval, while holding incoming catalog edits for custodian review, and
  4. **Blocked** rejects all incoming and outgoing friend requests, loan/collection requests, and catalog updates with that peer

#### Scenario: Add Instance dialog displays reciprocal peering note

- **WHEN** an administrator opens the "Add Instance" modal dialog
- **THEN** the dialog displays a clear, plain-language note that new peers start as **Untrusted** and that the remote server's administrator must also register this server on their end
