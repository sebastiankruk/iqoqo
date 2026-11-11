## ADDED Requirements

### Requirement: Redis Rate-Limit Storage Configuration Precedence and Standard Headers
The backend `Limiter` instance in `app/core/limiter.py` MUST NOT hardcode `storage_uri="memory://"` in the `Limiter(...)` constructor so that `app.config["RATELIMIT_STORAGE_URI"]` configured during `create_app()` in `app/__init__.py` takes precedence when `limiter.init_app(app)` executes. Furthermore, `create_app()` MUST enable `RATELIMIT_HEADERS_ENABLED` by default so responses include rate-limit diagnostic headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` on `429`).

#### Scenario: Configured Redis storage URI is honored by Flask-Limiter
- **GIVEN** `app.config["RATELIMIT_STORAGE_URI"]` is set to a valid Redis URL (or `memory://` fallback when Redis is unavailable) in `create_app()`
- **WHEN** `limiter.init_app(app)` initializes the rate limiter
- **THEN** `limiter._storage_uri` is `None` on the module-level `Limiter` instance so `app.config["RATELIMIT_STORAGE_URI"]` governs the active storage backend
- **AND** `app.config["RATELIMIT_HEADERS_ENABLED"]` is `True`

### Requirement: Calibrated Default Rate Limits and CORS OPTIONS Preflight Exemption
The global `default_limits` on `limiter` in `app/core/limiter.py` SHALL be configured to `["1000 per hour", "10000 per day"]` to accommodate normal SPA and mobile WebView navigation without throttling legitimate single-user sessions, while route-specific `@limiter.limit(...)` decorators on authentication, account management, user search, scanner, and federation endpoints remain strictly enforced. Additionally, HTTP `OPTIONS` preflight requests MUST be exempt from rate-limit accounting.

#### Scenario: Normal SPA and mobile browsing does not trigger 50/hour lockout
- **GIVEN** an authenticated user or client making more than 50 requests per hour to general API endpoints (such as `GET /api/profile/`, `GET /api/items`, or `GET /api/config`)
- **WHEN** the request rate remains within `1000 per hour` and `10000 per day`
- **THEN** the requests succeed with HTTP `200` and are not rejected with HTTP `429`

#### Scenario: CORS OPTIONS preflight requests do not consume rate-limit quota
- **GIVEN** a browser or Capacitor mobile WebView sends HTTP `OPTIONS` preflight requests before cross-origin API calls
- **WHEN** the rate limiter evaluates the `OPTIONS` request
- **THEN** the `OPTIONS` request is exempted via request filter and consumes zero tokens from the client's rate-limit bucket

### Requirement: Frontend Profile Hook Resilience Against HTTP 429 and Redundant Polling
The `useProfile()` hook in `frontend/lib/api/hooks/user.ts` MUST NOT interpret HTTP `429 Too Many Requests` or `5xx` server errors as an unauthenticated (`null`) user state when no offline snapshot is cached, preventing false-logout UI states and `/login` $\leftrightarrow$ `/profile` middleware redirect loops. Additionally, `useProfile()` SHALL use a non-zero `staleTime` (`30_000` ms) to avoid firing duplicate `GET /api/profile/` requests across co-mounted layout and page components.

#### Scenario: HTTP 429 on GET /api/profile/ does not log out the user or return null silently
- **GIVEN** a user has an active session and `GET /api/profile/` responds with HTTP `429 Too Many Requests`
- **WHEN** `useProfile()` handles the rejected request
- **THEN** it does NOT clear the native auth token
- **AND** if a cached profile snapshot is available it returns that snapshot; otherwise it rethrows the `429` error so TanStack Query retains prior data/error state instead of resolving `data: null` (which falsely indicates a logged-out user)

#### Scenario: HTTP 401 on GET /api/profile/ still resolves to null and clears native auth token
- **GIVEN** `GET /api/profile/` responds with HTTP `401 Unauthorized`
- **WHEN** `useProfile()` handles the rejected request
- **THEN** it clears any stored native auth token and returns `null`
