## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: safe_get docstring accuracy
The `safe_get()` function docstring SHALL accurately reflect the security guarantees provided, including redirect chain protection and socket-level IP pinning for HTTPS.

#### Scenario: Docstring matches implementation

- **WHEN** a developer reads the `safe_get()` docstring
- **THEN** the documented protections SHALL match the actual implementation behavior
