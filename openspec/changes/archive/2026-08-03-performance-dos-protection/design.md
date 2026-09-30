## Context

The application is currently vulnerable to resource exhaustion from unauthenticated, computationally expensive API endpoints. Specifically, the faceted stats endpoint (`/api/stats/facets`) involves complex nested database subqueries (`_build_item_ids_subq`) that, if hit repeatedly, could consume all database connections and CPU. We need to introduce rate limiting and caching backed by our existing Redis infrastructure to mitigate this risk and improve overall performance. Finally, we need a methodology to prove these changes are effective.

## Goals / Non-Goals

**Goals:**

- Implement global and route-specific API rate limiting using Flask-Limiter and Redis.
- Implement short-lived caching for the faceted stats endpoint.
- Develop load tests to run against a production clone to ensure our nested subqueries and caching strategies are performant.

**Non-Goals:**

- Completely rewriting the database schema to avoid subqueries.
- Implementing edge caching via a CDN (we are focusing on application-level caching).

## Decisions

### 1. Rate Limiting Implementation

- **Decision**: Use `Flask-Limiter` with a Redis storage backend in `app/core/limiter.py`.
- **Rationale**: `Flask-Limiter` is the standard, well-supported library for Flask rate limiting. Redis is already part of our stack, making it the ideal backend for distributed rate limit tracking across multiple application instances.

### 2. Caching Implementation

- **Decision**: Apply `@cache.memoize(timeout=300)` on the `/api/stats/facets` endpoint for unauthenticated users, or globally if the stats are not user-specific.
- **Rationale**: A 5-minute (300s) cache TTL is long enough to absorb a spike in traffic (DoS) while keeping data relatively fresh. Memoization ensures that identical query parameters return the cached response.

### 3. Load Testing Methodology

- **Decision**: Use an HTTP load testing tool (like Locust or standard parallel `curl`/`ab` via bash scripts) targeting a dedicated clone of the production database.
- **Rationale**: Testing on a clone ensures that we see real-world query execution plans and index usage without impacting actual users.

## Risks / Trade-offs

- [Risk] **Cache invalidation complexity** → Mitigation: By using a short TTL (300s) instead of manual invalidation logic, we avoid complex cache invalidation bugs at the cost of data being up to 5 minutes stale.
- [Risk] **Rate limit lockouts** → Mitigation: Start with generous limits and monitor 429 responses. Ensure internal IP ranges or admin accounts have bypasses if necessary.
