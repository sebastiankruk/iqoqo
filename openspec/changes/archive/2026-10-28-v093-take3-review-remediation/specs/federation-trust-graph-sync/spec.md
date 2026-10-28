## ADDED Requirements

### Requirement: Port-Preserving Metadata Sync, DER Key Fingerprinting, and Same-Origin Actor Discovery

The federation trust synchronization, cryptographic key fingerprinting, and peer discovery subsystems SHALL preserve non-standard ports when looking up `FederationInstance` trust in `reconcile_activity`, compute `SHA256:...` public key fingerprints from decoded ASN.1 DER `SubjectPublicKeyInfo` bytes, verify that NodeInfo `metadata.instance_actor` URLs share the exact normalized domain as the probed peer before fetching/caching actor keys, refresh cached instance actor keys cleanly during batch health probes without setting unmapped ORM attributes, exclude `.localdomain`/`.home.arpa`/`.lan` and bracketed IPv6 local addresses from the public directory, and bind the preview `peer-frontend` container port exclusively to `127.0.0.1`.

#### Scenario: Non-standard port on trusted hostname cannot spoof trusted metadata sync

- **WHEN** `trusted-peer.org` is `trusted` and an `Update` activity arrives from `https://trusted-peer.org:8443/u/rogue`
- **THEN** `reconcile_activity` queries `FederationInstance` using `trusted-peer.org:8443` rather than `trusted-peer.org` and refuses to auto-merge untrusted catalog metadata

#### Scenario: Public key fingerprint is invariant to PEM whitespace and line endings

- **WHEN** `compute_pem_fingerprint` evaluates the same RSA public key formatted with `\n` vs `\r\n` line endings or differing PEM armor whitespace (or receives invalid non-PEM text)
- **THEN** valid PEM inputs produce the identical DER-derived `SHA256:<hex>` digest and invalid/empty inputs return `"Not configured"`

#### Scenario: Cross-origin NodeInfo instance_actor URL is ignored during peer health probe

- **WHEN** probing `evil.example` returns a NodeInfo 2.1 document claiming `"metadata": {"instance_actor": "https://victim.example/api/federation/actor"}`
- **THEN** the health probe rejects the cross-origin `instance_actor` URL without fetching `victim.example` or polluting the local instance registry
