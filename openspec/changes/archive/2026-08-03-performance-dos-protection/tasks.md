## 1. Rate Limiting Setup

- [x] 1.1 Add `Flask-Limiter` dependency to `requirements.txt` / `pyproject.toml`
- [x] 1.2 Initialize the rate limiter using the Redis connection in `app/core/limiter.py`
- [x] 1.3 Apply global or route-specific rate limits to all relevant API endpoints

## 2. Faceted Stats Caching

- [x] 2.1 Integrate caching decorator (`@cache.memoize(timeout=300)`) on the `/api/stats/facets` endpoint
- [x] 2.2 Configure cache key generation to handle varying query parameters appropriately
- [x] 2.3 Write tests to verify that consecutive requests to the endpoint return cached data and do not hit the DB

## 3. Load Testing Implementation

- [x] 3.1 Create a database cloning script or procedure to spin up a production-like test DB
- [x] 3.2 Write a load testing script (e.g., using `locust` or a parallel bash script) targeting `_build_item_ids_subq` via the API
- [x] 3.3 Execute load tests and record baseline metrics without caching/limits
- [x] 3.4 Re-execute load tests with caching and limits enabled to document improvements
