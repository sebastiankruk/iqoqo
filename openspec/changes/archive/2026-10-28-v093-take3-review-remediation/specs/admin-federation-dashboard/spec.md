## ADDED Requirements

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
