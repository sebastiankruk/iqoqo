## ADDED Requirements

### Requirement: API Health Check Security and Performance

The API health check endpoint (`/api/health`) SHALL prevent DoS and OOM vulnerabilities during drift checks. The endpoint SHALL require authentication via an `X-Deploy-Token` header. When checking data drift (`check_drift=1`), the system SHALL use SQL aggregation (e.g., `func.count()`) instead of loading full ORM objects into memory, ensuring memory footprint remains flat regardless of database size.

#### Scenario: Unauthenticated health check request

- **WHEN** an unauthenticated client requests `/api/health?check_drift=1` without a valid `X-Deploy-Token` header
- **THEN** the system SHALL reject the request with a 401 Unauthorized or 403 Forbidden status

#### Scenario: Authenticated health check with drift validation

- **WHEN** an authenticated client with a valid `X-Deploy-Token` header requests `/api/health?check_drift=1`
- **THEN** the system SHALL compute the drift using SQL aggregations that do not load table rows into Python memory, preventing OOM crashes
