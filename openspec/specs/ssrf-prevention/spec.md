# ssrf-prevention Specification

## Purpose

Prevent Server-Side Request Forgery (SSRF) attacks when the system fetches external resources based on user-supplied or external URLs.
## Requirements
### Requirement: Prevent SSRF on External Fetches

The system MUST ensure that all requests to external resources (e.g., fetching images or API data based on user-supplied or external URLs) do not target restricted IP ranges (localhost, RFC 1918, AWS metadata).

#### Scenario: Attempting to fetch from localhost

- **WHEN** the application attempts to fetch a resource from `http://localhost/` or `http://127.0.0.1/`
- **THEN** the request is blocked and an error is raised or logged appropriately

#### Scenario: Attempting to fetch from cloud metadata endpoint

- **WHEN** the application attempts to fetch a resource from `http://169.254.169.254/`
- **THEN** the request is blocked and an error is raised or logged appropriately

#### Scenario: Attempting to fetch from a domain resolving to a private IP (DNS Rebinding protection)

- **WHEN** the application attempts to fetch a resource from a domain that resolves to an RFC 1918 address (e.g., `10.0.0.1`)
- **THEN** the request is blocked after DNS resolution and prior to the HTTP connection being made

### Requirement: DNS resolution timeout enforcement

The system SHALL enforce an explicit timeout on all `socket.getaddrinfo()` calls within the SSRF-safe HTTP client to prevent Celery worker threads from blocking indefinitely when resolving hostnames against malicious or unresponsive DNS servers. The timeout MUST be no greater than 5 seconds.

#### Scenario: DNS resolution completes within timeout

- **WHEN** the system resolves a hostname via `socket.getaddrinfo()` and the DNS server responds within 5 seconds
- **THEN** the resolution SHALL proceed normally and the resolved IP addresses SHALL be validated against `_BLOCKED_NETWORKS`

#### Scenario: DNS resolution hangs beyond timeout

- **WHEN** the system attempts to resolve a hostname via `socket.getaddrinfo()` and the DNS server does not respond within 5 seconds
- **THEN** the system SHALL raise an `SSRFError` with a descriptive message indicating DNS resolution timeout, and the Celery worker thread SHALL NOT remain blocked

