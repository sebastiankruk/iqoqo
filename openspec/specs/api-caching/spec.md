# api-caching Specification

## Purpose

Redis-backed response caching for expensive, high-frequency read operations such as faceted stats.

## Requirements

### Requirement: Faceted Stats Caching

The system MUST cache the responses of the `/api/stats/facets` endpoint for a defined duration (e.g., 300 seconds) to reduce database load from computationally expensive subqueries.

#### Scenario: Subsequent requests to faceted stats

- **WHEN** a client requests the faceted stats with identical query parameters within the cache TTL
- **THEN** the system serves the response directly from the Redis cache without executing the database query
