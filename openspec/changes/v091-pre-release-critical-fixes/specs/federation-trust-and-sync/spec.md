## MODIFIED Requirements

### Requirement: Local Hostname Verification and Input Sanitization in Federation Metadata Sync
`resolve_local_manifestation` and `sync_manifestation` in `app/core/federation_sync.py` SHALL verify that `/manifestation/<id>` URIs match the local instance hostname before querying by integer primary key, sanitize all inbound text strings with `bleach.clean`, and validate `http(s)` schemes on `cover_url`.

#### Scenario: Remote manifestation URI with foreign hostname does not collide with local primary key
- **WHEN** a remote peer sends a `Create` or `Update` activity whose object `id` is `https://remote.example/api/manifestations/1` and lacks matching ISBN/UPC/EAN identifiers
- **THEN** `resolve_local_manifestation` does not load local `Manifestation(id=1)` because `remote.example` does not match the local instance domain

#### Scenario: Malicious HTML and non-HTTP cover URLs are sanitized during sync
- **WHEN** a trusted or pending peer sends metadata containing HTML/script tags in `publisher` or `format` or a `javascript:`/`data:` URI in `cover_url`
- **THEN** `sync_manifestation` strips HTML tags via `bleach.clean(..., tags=[], strip=True)` and rejects non-`http(s)` `cover_url` values
