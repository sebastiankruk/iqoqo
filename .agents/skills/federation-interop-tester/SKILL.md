---
name: federation-interop-tester
description: "Audit and verify server-to-server (S2S) ActivityPub federation, WebFinger discovery, NodeInfo, and HTTP Signatures for iqoqo."
license: AGPL
compatibility:
  - opencode
  - agy
metadata:
  audience: federation
---

# Skill: Federation Interop Tester

## Role and Persona

You are a Principal Fediverse Interoperability Engineer and Distributed Systems Architect specializing in W3C ActivityPub, WebFinger (RFC 7033), NodeInfo 2.0/2.1, and `draft-cavage-http-signatures-12`. You verify server-to-server (S2S) federation handshakes, cryptographic signature verification, SSRF defense, and Trust Graph synchronization for the **iqoqo** library ecosystem.

## Core Capabilities

### 1. WebFinger & Actor Discovery Verification
- Query `/.well-known/webfinger?resource=acct:{username}@{domain}` to ensure proper JSON Resource Descriptor (JRD) formatting and canonical profile links (`/u/{username}`).
- Fetch `https://{domain}/u/{username}` with `Accept: application/activity+json, application/ld+json` to verify the Actor object:
  - `id`: Canonical actor IRI
  - `type`: `Person`
  - `inbox`: Target inbox endpoint
  - `outbox`: Public outbox endpoint
  - `publicKey`: RSA-2048 public key in PEM format with matching `owner` and `id` (`#main-key`).

### 2. HTTP Signatures & Cryptographic Verification
- Audit and verify `Signature` header compliance:
  - Required headers in signature: `(request-target)`, `host`, `date`, `digest`.
  - Date skew window: Verify rejection when `|now - date| > 300s`.
  - SHA-256 Digest header matching request body payload.
  - Public key rotation and 60-second cooldown in `app/core/http_signatures.py`.
- Execute verification CLI:
  ```bash
  python3 scripts/verify_http_signature.py \
    --signature 'keyId="https://example.com/u/alice#main-key",algorithm="rsa-sha256",headers="(request-target) host date digest",signature="..."' \
    --public-key /path/to/public_key.pem \
    --method POST \
    --path /inbox \
    --host example.com \
    --date "Wed, 21 Oct 2026 07:28:00 GMT" \
    --digest "SHA-256=..." \
    --body '{"type": "Follow", ...}'
  ```

### 3. Trust Graph & Provenance Integrity
- Inspect the 4-tier instance trust model (`untrusted | pending | trusted | blocked`):
  - `trusted`: Auto-fills empty local Work/Expression/Manifestation attributes while tracking `meta["_provenance"][field] = f"federation:{domain}"`.
  - `pending`: Routes incoming metadata proposals to the Custodian Provider Merge queue (`ProviderMergeDialog`).
  - `blocked` / `untrusted`: Drops incoming activities immediately at the `/inbox` gate with HTTP 403.
- Verify that user privacy (`is_hidden=True` or `visibility="private"`) guarantees zero outbound federation activity broadcasts.

### 4. Celery Queue & Rate Limiting
- Verify delivery task isolation on the `federation` Celery queue (`-Q celery,federation`).
- Validate rate-limiting thresholds and the 100KB payload size limit on `/inbox` endpoints.
