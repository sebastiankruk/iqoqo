## Context

See `proposal.md` for security audit findings and motivation. During `v0.9.3` pre-release verification across `preview.iqoqo.cc` and `peer.iqoqo.cc`, five interacting layers caused security and operational divergence:
1. `app/api/admin.py` defines `FEDERATION_KEYS = {"FEDERATION_ENABLED", "FEDERATION_BASE_URL"}`, omitting `FEDERATION_AUTO_ACCEPT_FOLLOWS` and `FEDERATION_DEFAULT_TRUST`, while `_put_settings` evaluates `key_permissions.get(key, True)` (fail-open). Meanwhile, `handle_follow` in `app/core/federation_handlers.py` calls `current_app.config.get("FEDERATION_AUTO_ACCEPT_FOLLOWS", True)` instead of `ConfigService.get_bool(..., default=False)`, and `app/config.py` never loads `FEDERATION_AUTO_ACCEPT_FOLLOWS`.
2. Domain normalization diverges between `clean_instance_domain` (retains non-80/443 ports), `FederationClient._cache_actor_in_db` (uses raw `urlparse.netloc` including `:443`), and `_get_or_create_actor` (uses `urlparse.hostname`, stripping all ports).
3. `get_key_fingerprint()` reads `data/keys/server.pem`, which is never generated anywhere, and no instance-level `Application` actor endpoint exists to publish `server.pem` or verify remote peer fingerprints without DDL changes.
4. `docker-compose.federation-preview.yml` overrides `FEDERATION_AUTO_ACCEPT_FOLLOWS=true` and lacks a shared `peer_data` volume between `peer-migration` and `peer-web`, while `scripts/verify_federation_preview.sh` commits `TrustLevel.TRUSTED` on `web:5000` / `peer-web:5000` into persistent preview volumes without cleanup, leaking internal Docker hostnames via `GET /api/federation/directory`.

## Goals / Non-Goals

**Goals:**
- Achieve zero-DDL security remediation suitable for immediate `v0.9.3` release without database schema migrations.
- Guarantee fail-closed RBAC and opt-in defaults (`FEDERATION_AUTO_ACCEPT_FOLLOWS=False`, `FEDERATION_DEFAULT_TRUST="untrusted"` clamped to `{"untrusted", "pending"}`).
- Unify `domain[:port]` canonicalization across discovery, outbound caching, and inbound handlers so port-scoped blocks cannot be bypassed.
- Make `Instance Actor Key Fingerprint` genuinely operational for out-of-band SHA-256 admin trust pinning and Authorized Fetch (`GET`) signing while strictly respecting the `State-Mutating Key Generation Restriction` (zero key generation on HTTP `GET`).
- Prevent internal Docker/RFC1918 hostnames from polluting persistent preview DBs or leaking through `/api/federation/directory`.

**Non-Goals:**
- Introducing new PostgreSQL columns or Alembic migrations on `federation.federation_instances` (we reuse `federation.federation_actors` to cache remote `Application` actors).
- Enforcing mandatory inbound Authorized Fetch rejection on public read-only endpoints (outbound `GET` signing is enabled when `server.pem` exists; inbound `GET /api/federation/actor*` remains readable for open Fediverse interoperability).

## Decisions

### 1. Zero-DDL Remote Instance Key Pinning via `FederationActor`
- **Choice**: Expose the local instance actor at `GET /api/federation/actor` (`type: "Application"`, `id: "{base_url}/api/federation/actor"`, `publicKey.id: "{base_url}/api/federation/actor#main-key"`) and advertise `"instance_actor": "{base_url}/api/federation/actor"` in `GET /api/federation/nodeinfo/2.1` `metadata`. During `discover_instance(domain)`, probe the advertised `instance_actor` URI (falling back to `{scheme}://{domain}/api/federation/actor`), store/update a `FederationActor` row tied to `instance.id` (`actor_uri == instance_actor_uri`), and compute `key_fingerprint` (`SHA256:<base64>`) directly from the DER encoding of `FederationActor.public_key_pem`. Batch-load matching instance actors in `list_federation_instances` to avoid N+1 queries.
- **Alternatives considered**:
  - *Add `public_key_pem` / `key_fingerprint` column to `FederationInstance`*: Requires an Alembic migration right before `v0.9.3` release tag; `FederationActor` already models `(instance_id, actor_uri, public_key_pem, last_fetched_at)` cleanly.
  - *Trust a `key_fingerprint` string in NodeInfo `metadata`*: Vulnerable to spoofing—an attacker or MITM could advertise victim's fingerprint string in NodeInfo while serving a different RSA key on actors. Computing SHA-256 from the actual `publicKeyPem` on `/api/federation/actor` binds the fingerprint cryptographically.

### 2. Side-Effect-Free `GET` vs. Bootstrap + Admin `POST` Key Provisioning
- **Choice**: Add `ensure_instance_actor_key() -> str` in `app/core/federation_keys.py` (calling `generate_actor_keypair("server")` if `server.pem` is absent and returning `get_key_fingerprint()`). Call it idempotently in `scripts/init_auth.py` (when `SECRET_KEY` is configured) AND expose `POST /api/v1/admin/federation/key-fingerprint/provision` (`@require_auth`, `@admin_required`, `PermissionName.CONFIG_FEDERATION`, optional `{"rotate": true}`, `EntityAuditLog`). `GET /api/federation/actor` and `GET /api/v1/admin/federation/key-fingerprint` remain strictly read-only.
- **Alternatives considered**:
  - *Lazy-generate `server.pem` on `GET /api/federation/actor`*: Violates `iqoqo-standards.md` ("A `GET` on such a route MUST NOT mutate state") and `federation-schema-and-keys` (`State-Mutating Key Generation Restriction`).

### 3. Bodyless `GET` HTTP Signatures (`draft-cavage-12`)
- **Choice**: Update `sign_request` in `app/core/http_signatures.py` so when `body is None` and `method.upper() in {"GET", "HEAD", "DELETE"}`, it signs `(request-target) host date` and omits the `Digest` header; when `body is not None` (all `POST`/`PUT` requests, including `b""`), it continues signing `(request-target) host date digest`. In `FederationClient.fetch_actor`, if `federation_keys.get_actor_private_key("server")` is available, sign the outbound `GET` with `key_id=f"{get_federation_base_url()}/api/federation/actor#main-key"`.
- **Rationale**: Matches `openspec/specs/activitypub-discovery-and-signatures/spec.md` ("include `(request-target)`, `host`, `date`, and (when body is present) `digest`") and Mastodon/BookWyrm/GoToSocial Authorized Fetch expectations.

### 4. Fail-Closed Settings RBAC & Clamped Default Trust
- **Choice**:
  - Expand `FEDERATION_KEYS` in `app/api/admin.py` to `{"FEDERATION_ENABLED", "FEDERATION_BASE_URL", "FEDERATION_AUTO_ACCEPT_FOLLOWS", "FEDERATION_DEFAULT_TRUST"}`.
  - In `_get_settings`, check `if key in db_settings` before falling back to `flask_config` / `os.environ` / explicit defaults (`FEDERATION_AUTO_ACCEPT_FOLLOWS="false"`, `FEDERATION_DEFAULT_TRUST="untrusted"`).
  - In `_put_settings`, change `key_permissions.get(key, True)` to fail closed: reject unknown keys (`400`) and unauthorized category keys (`403`), validate `FEDERATION_DEFAULT_TRUST in {"untrusted", "pending"}` (`400` otherwise), validate `FEDERATION_AUTO_ACCEPT_FOLLOWS` boolean/string (`"true"`/`"false"`), and log `EntityAuditLog` (`entity_type="instance_settings"`) on federation setting updates.
  - Clamp `FEDERATION_DEFAULT_TRUST` via a shared helper `get_safe_default_trust()` returning `TrustLevel.PENDING` only if configured to `"pending"`, else `TrustLevel.UNTRUSTED`.

### 5. Public Directory Routable-Domain Filter & Ephemeral Preview Smoke Cleanup
- **Choice**: Add `is_publicly_routable_peer_domain(domain: str) -> bool` (stripping port, rejecting `localhost`, single-label container names without `.`, `.local`, `.internal`, `.test`, `.invalid`, and `ipaddress` private/loopback/link-local/reserved literals) and apply it in `get_federation_directory` (`app/api/federation.py`). In `scripts/verify_federation_preview.sh`, capture whether `peer-web:5000` / `web:5000` existed beforehand and delete synthetic smoke-test rows in a `finally:` block. Mount `peer_data:/usr/src/app/data` on `peer-migration` and `peer-web` in `docker-compose.federation-preview.yml`.

## Risks / Trade-offs

- **[Risk] Existing unit tests calling `federation_keys` outside Flask app context without `SECRET_KEY` env var** -> **Mitigation**: `tests/conftest.py` and app fixtures set `SECRET_KEY`; audit all `federation_keys` unit tests during implementation to ensure `SECRET_KEY` is explicitly configured rather than relying on the removed insecure fallback.
- **[Risk] Signing outbound `FederationClient.fetch_actor` GETs when `FEDERATION_BASE_URL` is unset in isolated unit tests** -> **Mitigation**: Guard outbound `GET` signing with `try/except` and only sign when `get_actor_private_key("server")` is present on disk so unit tests mocking `safe_get` without `server.pem` behave identically unless testing signed fetch.
- **[Risk] Stale `web:5000` row already persisted in operator's local `peer_postgres_data` volume** -> **Mitigation**: Document cleanup and also purge stale synthetic `web:5000` / `peer-web:5000` rows in `verify_federation_preview.sh` `finally` block (and on live running preview containers).

## Migration Plan

1. Zero database DDL migrations required (`len(ScriptDirectory.get_heads()) == 1` preserved).
2. On upgrade/restart of `v0.9.3`, `init_auth.py` automatically generates `data/keys/server.pem` if absent; admins on already-running containers without restart can also click **Generate Instance Key** in `/admin/federation` -> Settings.
3. Rollback is a pure container image rollback with zero schema impact.
