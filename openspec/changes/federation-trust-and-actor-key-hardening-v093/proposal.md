## Why

Manual pre-release security testing of the dual-instance federation preview stack (`preview.iqoqo.cc` and `peer.iqoqo.cc`) uncovered a cluster of critical, high, medium, and low security, SRE, and UX defects: `handle_follow` silently auto-accepts 100% of follow requests (`True`) while the Admin UI misrepresents `Auto-Accept Follow Requests` as `Disabled` because `FEDERATION_AUTO_ACCEPT_FOLLOWS` and `FEDERATION_DEFAULT_TRUST` are omitted from `FEDERATION_KEYS` and `Config`; `_put_settings` fails open (`True`) on unknown setting keys; port-stripping in `_get_or_create_actor` permits blocklist bypass for peers on non-standard ports; the Instance Actor Key (`data/keys/server.pem`) is never provisioned (`"Not configured"`) and lacks a public `Application` actor endpoint for out-of-band SHA-256 trust pinning; `peer-web` loses cryptographic keys across container restarts due to a missing `peer_data` volume; and `verify_federation_preview.sh` leaves `TRUSTED` internal Docker hostnames (`web:5000`) in persistent databases that leak through the public `/federation/directory` endpoint. Resolving all findings in `v0.9.3` is essential before cutting today's release.

## What Changes

- **Enforce `FEDERATION_AUTO_ACCEPT_FOLLOWS` (default `False`) & Settings RBAC Fail-Closed**:
  - Register `FEDERATION_AUTO_ACCEPT_FOLLOWS` (default `False`) and `FEDERATION_DEFAULT_TRUST` (default `"untrusted"`) in `app/config.py`, `.env.example`, and `FEDERATION_KEYS` in `app/api/admin.py`.
  - Update `handle_follow` (`app/core/federation_handlers.py`) to read `ConfigService.get_bool("FEDERATION_AUTO_ACCEPT_FOLLOWS", default=False)` instead of `current_app.config.get(..., True)`.
  - Fix `_get_settings` (`app/api/admin.py`) to check key membership (`key in db_settings`) rather than truthiness, and harden `_put_settings` to fail closed (`key_permissions.get(key, False)`), reject unknown keys or invalid `FEDERATION_DEFAULT_TRUST` values outside `{"untrusted", "pending"}` with HTTP `400`/`403`, and write `EntityAuditLog` entries for federation configuration mutations.
  - Remove `FEDERATION_AUTO_ACCEPT_FOLLOWS=true` overrides from `docker-compose.federation-preview.yml` so preview matches production's secure default (`Disabled`).
- **Eliminate Domain/Port Blocklist Bypass, Clamp Default Trust & Filter Public Directory**:
  - Normalize peer domains consistently via `clean_instance_domain` across `discover_instance` (`app/core/federation_discovery.py`), `_get_or_create_actor` (`app/core/federation_handlers.py`), and `FederationClient._cache_actor_in_db` (`app/core/federation_client.py`) so non-standard ports (`domain:8443`, `localhost:5005`) never split into unblocked portless records.
  - Clamp `FEDERATION_DEFAULT_TRUST` to `{"untrusted", "pending"}` in both `discover_instance` and `_get_or_create_actor`, and emit `EntityAuditLog` (`change_type="instance_added"`) in `add_federation_instance` (`app/api/admin.py`).
  - Filter internal, single-label, loopback, `.local`/`.internal`, and private-IP hostnames (e.g., `web:5000`, `peer-web:5000`, `localhost`) out of the unauthenticated public `GET /api/federation/directory` response (`app/api/federation.py`).
- **Provision Instance Actor Key (`server.pem`), Expose `Application` Actor & Enable Peer Key Pinning**:
  - Remove the hardcoded dev fallback secret in `app/core/federation_keys.py` (`_get_fernet_cipher`), failing closed with `RuntimeError` when `SECRET_KEY` is absent.
  - Provision `data/keys/server.pem` idempotently during bootstrap in `scripts/init_auth.py` and via an explicit authenticated `POST /api/v1/admin/federation/key-fingerprint/provision` endpoint (`@require_auth`, `@admin_required`, `PermissionName.CONFIG_FEDERATION`, `EntityAuditLog`), never during `GET` requests.
  - Expose read-only `GET /api/federation/actor` (`Application` actor JSON-LD publishing `#main-key`, returning `404` if unprovisioned) and advertise `instance_actor` in NodeInfo 2.1 `metadata`; support bodyless `GET` HTTP Signatures (`(request-target) host date`) in `sign_request` and sign outbound `FederationClient.fetch_actor` GETs when `server.pem` is available.
  - Fetch and cache remote peer `Application` actor public keys during `discover_instance`, surface verified SHA-256 `key_fingerprint` values on `GET /api/v1/admin/federation/instances`, add a `"Generate / Rotate Instance Key"` control in `instance-settings.tsx`, display peer key fingerprints in `federation-instances.tsx` (`en.json` / `pl.json`), and document new endpoints in `app/api/docs.py` (OpenAPI 3.1).
- **Harden Dual-Instance Preview Persistence, Smoke Cleanup & Documentation**:
  - Mount a dedicated `peer_data:/usr/src/app/data` named volume on `peer-migration` and `peer-web` in `docker-compose.federation-preview.yml` so peer RSA keys survive container recreation.
  - Wrap Step 8 of `scripts/verify_federation_preview.sh` in `try ... finally` cleanup so synthetic `web:5000` / `peer-web:5000` `TRUSTED` rows are never left behind in persistent preview databases.
  - Update `.context/notes/tests/federation-manual-testing-walkthrough.md`, `docs/SECURITY.md`, `docs/API.md`, and `docs/CHANGELOG.md` with full Federation Settings, SHA-256 Instance Key Fingerprint verification, and clean dual-instance peering documentation.

## Capabilities

### New Capabilities
<!-- None; all changes strengthen existing federation, admin, discovery, key-lifecycle, directory, and preview capabilities. -->

### Modified Capabilities
- `activitypub-inbox-outbox`: Enforce `ConfigService.get_bool("FEDERATION_AUTO_ACCEPT_FOLLOWS", default=False)` in `handle_follow`, normalize inbound actor domains via `clean_instance_domain`, and clamp `FEDERATION_DEFAULT_TRUST` to `untrusted` or `pending`.
- `admin-federation-dashboard`: Return `FEDERATION_AUTO_ACCEPT_FOLLOWS` and `FEDERATION_DEFAULT_TRUST` in admin settings, enforce fail-closed RBAC allowlisting and enum validation (`untrusted` | `pending`) on `PUT /api/v1/admin/settings`, add explicit admin Instance Actor Key provisioning UI/API, and display verified remote peer SHA-256 key fingerprints in the instances table.
- `federation-trust-graph-sync`: Unify domain+port normalization across discovery, client caching, and inbound handlers to prevent port-stripping blocklist bypasses; audit-log `add_federation_instance`; and resolve/verify remote Instance `Application` Actor key fingerprints during peer discovery.
- `federation-schema-and-keys`: Provision Fernet-encrypted `server.pem` via `init_auth.py` and authenticated admin `POST` (never `GET`), fail closed when `SECRET_KEY` is missing in `federation_keys.py`, and persist peer key storage via `peer_data` volume.
- `activitypub-discovery-and-signatures`: Expose read-only `GET /api/federation/actor` (`Application` actor), advertise `instance_actor` in NodeInfo 2.1 metadata, and sign bodyless `GET` requests (`(request-target) host date`) with the Instance Actor Key for Authorized Fetch compatibility.
- `federation-index-and-docs`: Exclude internal, single-label, loopback, and private-IP peer domains (`web:5000`, `localhost`, etc.) from the public unauthenticated `/api/federation/directory` listing.
- `federation-multi-instance-e2e`: Clean up synthetic `web:5000` / `peer-web:5000` trust fixtures in `verify_federation_preview.sh`, remove insecure `FEDERATION_AUTO_ACCEPT_FOLLOWS=true` compose overrides, persist `peer_data`, and document settings + key-pinning workflows in manual walkthrough and release docs.

## Impact

- **Backend**: `app/config.py`, `app/api/admin.py`, `app/api/federation.py`, `app/api/docs.py`, `app/core/federation_handlers.py`, `app/core/federation_discovery.py`, `app/core/federation_client.py`, `app/core/federation_keys.py`, `app/core/http_signatures.py`, `scripts/init_auth.py`.
- **Frontend**: `frontend/components/admin/instance-settings.tsx`, `frontend/components/admin/federation-instances.tsx`, `frontend/lib/api/federation.ts`, `frontend/types/federation.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Infrastructure & Scripts**: `docker-compose.federation-preview.yml`, `scripts/verify_federation_preview.sh`, `.env.example`.
- **Documentation & Tests**: `.context/notes/tests/federation-manual-testing-walkthrough.md`, `.context/notes/plan/0.9.x-release-plan.md`, `docs/SECURITY.md`, `docs/API.md`, `docs/CHANGELOG.md`, backend `pytest` suites, frontend `Vitest` suites, and BATS checks.
