## Why
To join the Fediverse, an iqoqo instance must be discoverable via standard protocols (WebFinger, NodeInfo) and authenticate outbound/inbound requests using draft-cavage-http-signatures-12 with SSRF defenses.
## What Changes

- Implement discovery endpoints: `GET /.well-known/webfinger`, `GET /.well-known/nodeinfo`, `GET /api/federation/nodeinfo/2.1`, `GET /api/federation/actor/{username}` (`application/activity+json`).
- Add `@federation_required` guard decorator in `app/api/federation_guard.py`.
- Implement HTTP Signatures signing and verification in `app/core/http_signatures.py` (`draft-cavage-http-signatures-12`).
- Enforce +/-300s Date skew validation, SHA-256 Digest header checks, and actor vs. keyId domain matching.
- Implement `app/core/federation_client.py` wrapping `app/utils/http_client.py` with SSRF socket-level IP pinning.
- Add `/.well-known/` proxy rules to `deploy/nginx.conf` and `deploy/nginx.conf.example`.

## Capabilities

### New Capabilities
- `activitypub-discovery-and-signatures`: WebFinger, NodeInfo 2.1, Actor JSON-LD endpoints, draft-cavage-12 HTTP Signatures, and SSRF-safe FederationClient

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Exposes public discovery endpoints, adds HTTP Signature crypto verification, and provides secure outbound client.
