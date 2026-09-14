# security-and-secrets Specification

## Purpose

Defines requirements for encrypting sensitive instance settings at rest, masking credentials in administrative responses, enforcing strict rate limits on authentication interfaces, and removing dead metric collection surfaces.

## Requirements

### Requirement: Sensitive Instance Settings Encryption at Rest
The system SHALL transparently encrypt all defined sensitive credential keys and dynamic OAuth tokens before storing them in `catalog.instance_settings` and decrypt them upon retrieval using symmetric encryption keyed from the application `SECRET_KEY`.

#### Scenario: Storing sensitive API key or token

- **WHEN** an administrator or background task persists a key from the sensitive registry (including `ALLEGRO_TOKEN_DATA`, `TMDB_API_READ_ACCESS_TOKEN`, and external API client secrets)
- **THEN** the value stored in the database is an encrypted ciphertext blob rather than plaintext JSON

#### Scenario: Retrieving sensitive API key or token

- **WHEN** the application requests a sensitive setting value via `get_value`
- **THEN** the setting is transparently decrypted and returned as the original plaintext string or data structure

### Requirement: Administrative Secret Masking and Rate Limiting
The system SHALL mask all registered sensitive keys in administrative settings responses, prohibit secret disclosure via HTTP GET query parameters, and enforce rate limits and audit logs on secret reveal endpoints.

#### Scenario: Viewing settings list in admin UI

- **WHEN** an administrator queries the settings endpoint
- **THEN** all sensitive credentials and token data are masked with asterisks in the JSON response

#### Scenario: Revealing sensitive setting via POST

- **WHEN** an administrator sends an authenticated HTTP POST request to reveal a secret
- **THEN** the request is rate-limited to 5 requests per minute, returns the decrypted value, and logs an entry to the entity audit log

### Requirement: Secure Authentication Exchange and Comparison
The system SHALL require POST payloads for authentication token exchanges, compare authentication tokens in constant time using `hmac.compare_digest`, and track explicit expiration timestamps on blocklisted tokens.

#### Scenario: Exchanging authentication code

- **WHEN** a client completes an OAuth authentication flow
- **THEN** code and token parameters are transmitted exclusively in the HTTP request body and never in the URL query string

#### Scenario: Checking token validity against blocklist

- **WHEN** an incoming bearer token is validated against the revoked token blocklist
- **THEN** the system verifies tokens using constant-time comparison and prunes expired tokens based on their expiration timestamp

### Requirement: Decommissioning of Prometheus Metrics Endpoint
The system SHALL eliminate the unauthenticated `/metrics` endpoint and remove the `prom-client` dependency, standardizing on OpenObserve and OpenTelemetry Collector for observability.

#### Scenario: Accessing /metrics endpoint

- **WHEN** any client attempts to access `/metrics`
- **THEN** the system returns HTTP 404 Not Found without executing telemetry collection or exposing system metrics
