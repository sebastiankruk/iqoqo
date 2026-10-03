## Why

To ensure the stability, performance, and availability of the application under heavy load or malicious traffic, we need to introduce robust DoS protection and performance optimizations. Specifically, the API lacks strict rate limiting, and complex faceted stats queries are currently uncached and unoptimized, making them prime targets for resource exhaustion.

## What Changes

- Integrate end-to-end API rate limiting using Redis in `app/core/limiter.py`.
- Implement Redis caching (`@cache.memoize(timeout=300)`) for unauthenticated faceted stats queries specifically on `/api/stats/facets`.
- Establish and execute a concurrent load testing suite against faceted stats nested subqueries (`_build_item_ids_subq`) on a production DB clone to validate performance improvements and rate limiting effectiveness.

## Capabilities

### New Capabilities

- `api-rate-limiting`: System-wide API rate limiting backed by Redis to prevent abuse and DoS attacks.
- `api-caching`: Redis-backed response caching for expensive, high-frequency read operations like faceted stats.
- `load-testing`: Framework and procedures for executing concurrent load tests against critical database queries.

### Modified Capabilities

## Impact

- `app/core/limiter.py` and API route definitions.
- `app/api/stats.py` or wherever `/api/stats/facets` is defined.
- Test suite and database cloning scripts.
