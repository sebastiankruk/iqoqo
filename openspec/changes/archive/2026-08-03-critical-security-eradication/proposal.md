## Why

There are two critical security vulnerabilities present in our application that must be eradicated immediately. First, the application is susceptible to Server-Side Request Forgery (SSRF) when fetching external API images. Second, parsing XML payloads from sources like BGG and MusicBrainz using `xml.etree.ElementTree` makes the system vulnerable to XML External Entity (XXE) Denial of Service attacks. These flaws must be patched to ensure the security and stability of the platform.

## What Changes

- Implement a strict, SSRF-safe HTTP client wrapper for fetching external images. This wrapper will enforce IP and domain whitelisting, explicitly blocking localhost, metadata endpoints (e.g., 169.254.169.254), and RFC 1918 private IP addresses.
- Replace all occurrences of `xml.etree.ElementTree` with `defusedxml.ElementTree` to safely parse XML payloads during ingestion (e.g., from BGG, MusicBrainz) and prevent XXE DoS attacks.

## Capabilities

### New Capabilities

- `ssrf-prevention`: A hardened HTTP client wrapper specifically designed to prevent Server-Side Request Forgery when interacting with external resources.
- `xxe-prevention`: Safe XML parsing mechanisms replacing standard vulnerable parsers to prevent XXE Denial of Service.

### Modified Capabilities

## Impact

- All ingestion utilities that fetch images from external URLs.
- All ingestion utilities that parse XML (BGG API parsers, MusicBrainz API parsers, etc.).
- Python dependencies (adding `defusedxml` if not present).
