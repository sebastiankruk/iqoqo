## 1. Dependency Management

- [x] 1.1 Verify if `defusedxml` is in `requirements.txt` / `pyproject.toml`; add it if missing.

## 2. SSRF Prevention Implementation

- [x] 2.1 Create a new HTTP client wrapper module (e.g., `app/utils/http_client.py`).
- [x] 2.2 Implement IP/domain whitelisting and block logic (blocking localhost, metadata endpoints 169.254.169.254, RFC 1918).
- [x] 2.3 Refactor existing external image fetching utilities to use the new SSRF-safe client.
- [x] 2.4 Write unit tests for the SSRF-safe client to ensure it correctly blocks malicious IPs and handles DNS rebinding safely.

## 3. XXE DoS Prevention Implementation

- [x] 3.1 Identify all usages of `xml.etree.ElementTree` in the codebase (specifically in BGG and MusicBrainz parsers).
- [x] 3.2 Replace standard imports with `defusedxml.ElementTree` and adjust parsing code if necessary.
- [x] 3.3 Run existing tests to ensure no regressions in XML parsing behavior.
- [x] 3.4 Write tests to verify that malicious XML entities are rejected by the new parser.
