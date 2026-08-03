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
