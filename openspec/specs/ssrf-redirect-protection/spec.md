# ssrf-redirect-protection Specification

## Purpose

Prevent SSRF redirect chain exploits and enforce socket-level IP pinning.

## Requirements

### Requirement: SSRF redirect chain prevention

The system SHALL disable automatic HTTP redirects in `safe_get()` and implement a manual redirect loop capped at 5 hops. On each redirect hop, the system SHALL re-resolve DNS and re-validate all resolved IPs against `_BLOCKED_NETWORKS` before following the `Location` header.

#### Scenario: Redirect to internal IP blocked

- **WHEN** an external URL returns HTTP 302 redirecting to `http://169.254.169.254/latest/meta-data/`
- **THEN** the system SHALL raise `SSRFError` and not follow the redirect

#### Scenario: Redirect chain exceeds max hops

- **WHEN** a URL chains more than 5 sequential redirects
- **THEN** the system SHALL raise `SSRFError` with a "too many redirects" message

### Requirement: HTTPS DNS rebinding protection via socket pinning

The system SHALL implement an `SSRFProtectionAdapter` that uses custom connection pools to pin socket-level connections to the pre-validated IP address for HTTPS requests while preserving SNI for TLS certificate validation.

#### Scenario: DNS rebinding attempt on HTTPS

- **WHEN** a hostname resolves to a safe IP during validation but re-resolves to `127.0.0.1` at connect time
- **THEN** the system SHALL connect to the originally validated IP, not the re-resolved one

### Requirement: safe_get docstring accuracy

The `safe_get()` function docstring SHALL accurately reflect the security guarantees provided, including redirect chain protection and socket-level IP pinning for HTTPS.

#### Scenario: Docstring matches implementation

- **WHEN** a developer reads the `safe_get()` docstring
- **THEN** the documented protections SHALL match the actual implementation behavior

### Requirement: Type-safe redirect URL joining

The system SHALL enforce `str()` coercion on both `current_url` and `next_url` arguments before calling `urllib.parse.urljoin()` within the `safe_get()` redirect loop to prevent `TypeError` crashes caused by non-string redirect header values.

#### Scenario: Redirect with well-formed string Location header

- **WHEN** an external URL returns HTTP 302 with a valid string `Location` header
- **THEN** the system SHALL join the current URL and redirect target using `urljoin(str(current_url), str(next_url))` and proceed with the next hop validation

#### Scenario: Redirect with non-string Location header value

- **WHEN** an external URL returns a redirect response where `response.headers.get("location")` yields a non-string type (e.g., bytes or mock object)
- **THEN** the system SHALL coerce the value to a string via `str()` before passing to `urljoin()`, preventing a `TypeError` crash in the Celery worker
