## ADDED Requirements

### Requirement: DNS resolution timeout enforcement

The system SHALL enforce an explicit timeout on all `socket.getaddrinfo()` calls within the SSRF-safe HTTP client to prevent Celery worker threads from blocking indefinitely when resolving hostnames against malicious or unresponsive DNS servers. The timeout MUST be no greater than 5 seconds.

#### Scenario: DNS resolution completes within timeout

- **WHEN** the system resolves a hostname via `socket.getaddrinfo()` and the DNS server responds within 5 seconds
- **THEN** the resolution SHALL proceed normally and the resolved IP addresses SHALL be validated against `_BLOCKED_NETWORKS`

#### Scenario: DNS resolution hangs beyond timeout

- **WHEN** the system attempts to resolve a hostname via `socket.getaddrinfo()` and the DNS server does not respond within 5 seconds
- **THEN** the system SHALL raise an `SSRFError` with a descriptive message indicating DNS resolution timeout, and the Celery worker thread SHALL NOT remain blocked
