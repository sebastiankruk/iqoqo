# federation-head-showcase-mode Specification

## Purpose
Configure and operate `iqoqo.cc` as a read-only Federation Hub and showcase coordinator where physical library items are synchronized from peered community instances via ActivityPub, while authenticated users can search the federated catalog, manage personal Wishlists (`UserWorkIntent`), and participate in social federation without creating local physical `Item` records.

## Requirements

### Requirement: Federation Head Mode Configuration & Public Discovery
The system SHALL support a `FEDERATION_HEAD_MODE` boolean configuration (persisted in `InstanceSettings` and fallback `Config.FEDERATION_HEAD_MODE`, default `False`) and expose `federation_head_mode: boolean` in `GET /api/config` and `metadata.federationHead: boolean` in `GET /.well-known/nodeinfo/2.1`.

#### Scenario: Public config advertises Federation Head mode

- **GIVEN** `FEDERATION_HEAD_MODE` is enabled (`"true"`) in `InstanceSettings` or environment configuration
- **WHEN** an unauthenticated or authenticated client requests `GET /api/config`
- **THEN** the response returns HTTP `200` with `data.federation_head_mode = true` alongside `federation_enabled`, `version`, and `maintenance_mode`.

#### Scenario: Admin toggles Federation Head mode in Federation Settings

- **GIVEN** an authenticated user with `config:federation` permission
- **WHEN** the user updates `FEDERATION_HEAD_MODE` via `PUT /api/admin/settings`
- **THEN** the setting is persisted in `InstanceSettings` and immediately reflected in subsequent `GET /api/config` responses without restarting the server.

### Requirement: Physical Item Write Guard with Wishlist & ActivityPub S2S Preservation
When `FEDERATION_HEAD_MODE` is enabled, the backend SHALL reject local physical `Item` creation (`POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk` with non-wishlist status, and `POST /api/scan` unless `policy == "wishlist"` or `collection_status == "wish_list"`) with HTTP `403 Forbidden` and structured JSON `{"error": "...", "code": 403}`, while allowing Wishlist (`UserWorkIntent`) mutations, `GET /api/scanner/preview/<query>`, ActivityPub S2S inbox synchronization (`/ap/inbox`), and admin/custodian metadata curation.

#### Scenario: Authenticated user attempts to add a physical item on Federation Head

- **GIVEN** `FEDERATION_HEAD_MODE` is `true` and a standard authenticated user has a valid session
- **WHEN** the user sends `POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk`, or `POST /api/scan` with `collection_status="available"`
- **THEN** the server rejects the request with HTTP `403` and JSON `{"error": "This instance operates as a read-only Federation Hub. Physical items are synchronized from connected community nodes; you may still add works to your Wishlist.", "code": 403}` and creates zero `Item` rows.

#### Scenario: Authenticated user adds a work to Wishlist on Federation Head

- **GIVEN** `FEDERATION_HEAD_MODE` is `true` and a user is logged in
- **WHEN** the user creates a wishlist entry via `POST /api/wishlist` or `POST /api/scan` with `policy="wishlist"` (`collection_status="wish_list"`)
- **THEN** the server permits the operation (`200`/`201`) and records the `UserWorkIntent` without creating a physical `Item`.

#### Scenario: Peered community node synchronizes catalog activity to Federation Head

- **GIVEN** `FEDERATION_HEAD_MODE` is `true` and a trusted remote peer sends an HTTP-Signature-verified ActivityPub activity to `/ap/inbox`
- **WHEN** the Federation Head processes the inbound activity
- **THEN** the synchronized `Work`, `Expression`, `Manifestation`, and federated provenance records are ingested normally without being blocked by the local user item write guard.

### Requirement: Federation Hub Badge, Dismissible Banner & Action-Density-Compliant Navigation
When `federation_head_mode` is `true`, the frontend SHALL render a `"Federation Hub · Read-Only"` badge in the top navigation bar, an optional dismissible informational banner linking to `/federation/directory`, tailored landing Hero and authenticated Dashboard copy (defaulting `StatsCards` to `Global` scope), and SHALL replace the local `Scan` navigation CTA with `Directory` (`/federation/directory`) while displaying a clean Federation Hub notice on `/scan`.

#### Scenario: Visitor or logged-in user views Navbar and Landing/Dashboard on Federation Head

- **GIVEN** `GET /api/config` returns `federation_head_mode: true`
- **WHEN** the user loads `/` or any page with `Navbar`
- **THEN** the navbar displays the `"Federation Hub · Read-Only"` badge, hides the desktop `Scan` button, replaces the mobile bottom-nav `Scan` tab with `Directory` (`/federation/directory`), defaults authenticated `StatsCards` to `Global` repository scope, and keeps visible action buttons within the UX density budget.

#### Scenario: User navigates directly to `/scan` on Federation Head

- **GIVEN** `federation_head_mode` is `true`
- **WHEN** the user navigates to `/scan`
- **THEN** the page renders a Shadcn Federation Hub read-only notice card with direct links to **Explore Federated Catalog** (`/collection`) and **Connected Libraries** (`/federation/directory`) instead of starting the physical item camera ingestion flow.
