# Why

Production incident analysis (`🪳 Prod Login Lockout — Rate Limiter Defect Stack.md`) uncovered a compounding 4-defect failure stack in `v1.0.1` that locks out legitimate single-user and mobile Capacitor collectors on `iqoqo.kruk.cc` with an infinite `/login` $\leftrightarrow$ `/profile` redirect loop:

1. **Defect 1 — Miscalibrated Default Rate Limits (`app/core/limiter.py:33`)**: `default_limits=["200 per day", "50 per hour"]` applies to every route without an explicit `@limiter.limit` override, including `GET /api/profile/`, `GET /api/items`, `GET /api/manifestations/*`, and `GET /api/config`. A single user navigating the SPA and Capacitor mobile app generated 184 requests in ~2 hours (~75 req/hr peak), hitting the `50 per hour` wall during normal browsing.
2. **Defect 2 — Constructor `storage_uri="memory://"` Silently Defeats Redis Storage (`app/core/limiter.py:34` vs `app/__init__.py:253`)**: `limiter = Limiter(..., storage_uri="memory://")` passes `storage_uri` directly to the constructor. In `flask-limiter 4.1.1`, `Limiter.init_app()` evaluates `self._storage_uri or app.config.get("RATELIMIT_STORAGE_URI")`—meaning the constructor's `"memory://"` **always wins** over `app.config["RATELIMIT_STORAGE_URI"] = redis_url` set in `app/__init__.py:253`. As a result, Redis holds zero rate-limit keys in production, each Gunicorn worker tracks isolated in-memory counters, and operators cannot inspect or flush rate-limit buckets via `redis-cli` without restarting the `web` container.
3. **Defect 3 — Unauthenticated CORS `OPTIONS` Preflights Consume Rate-Limit Quota (`app/core/limiter.py:18-30`)**: Browser and Capacitor WebView `OPTIONS` preflight requests carry no `Authorization` header or session cookie, falling back to `get_remote_address()` in `get_user_id_or_ip()` and double-spending rate-limit quota on cross-origin mobile traffic.
4. **Defect 4 — Frontend `useProfile()` Treats HTTP `429` as Logged-Out (`frontend/lib/api/hooks/user.ts:32-55`)**: When `GET /api/profile/` returns HTTP `429 Too Many Requests`, `useProfile()` catches the error and falls through to `getCachedProfileSnapshot()`. On web browsers where no offline snapshot exists (and with `staleTime: 0` re-fetching `/api/profile/` 2–3 times per page transition), `useProfile()` returns `null`, causing the client UI to render the logged-out state while Next.js edge middleware (`frontend/proxy.ts`) sees the valid `session` cookie and redirects `/login` $\to$ `/profile` in an infinite bounce loop.

## What Changes

- **Recalibrate Default Rate Limits & Exempt `OPTIONS` Preflights (`app/core/limiter.py`)**:
  - Raise `default_limits` from `["200 per day", "50 per hour"]` to `["1000 per hour", "10000 per day"]` (~13× headroom over observed single-user peak while blocking runaway scrapers).
  - Preserve strict per-route limits on sensitive endpoints (`/api/auth/login` `20/min`, `/api/auth/register` `20/min`, account operations `3/hour`, `/api/users/search` `30/min`, `/api/scan` `10/min`, federation endpoints).
  - Add `@limiter.request_filter` (or `default_limits_exempt_when`) exempting `request.method == "OPTIONS"` so CORS preflights never consume rate-limit quota.
- **Restore Redis Rate-Limit Storage Precedence & Standard Headers (`app/core/limiter.py`, `app/__init__.py`)**:
  - Remove `storage_uri="memory://"` from the `Limiter(...)` constructor in `app/core/limiter.py` so `Limiter.init_app(app)` honors `app.config["RATELIMIT_STORAGE_URI"]` (which `app/__init__.py` sets to `redis_url` when `RATELIMIT_STORAGE_URI` or `REDIS_URL` is reachable, and falls back to `"memory://"` when Redis is disabled or unreachable).
  - Enable `app.config.setdefault("RATELIMIT_HEADERS_ENABLED", True)` in `app/__init__.py` so `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` headers are emitted on responses.
- **Harden `useProfile()` Against HTTP `429` Lockout & Reduce Redundant Polling (`frontend/lib/api/hooks/user.ts`)**:
  - Distinguish authentication failures (`401`, `403`, `404`) from transient throttling/server errors (`429`, `5xx`) in `useProfile()`:
    - On `401` / `404`: clear native auth token (if `401`) and return `null` (genuinely unauthenticated).
    - On `429` or `5xx`: return cached profile snapshot (`queryClient.getQueryData(["profile"])` or `getCachedProfileSnapshot()`) if available, or rethrow the error so TanStack Query preserves the previous data/error state instead of overwriting `user` with `null` (which falsely triggers logged-out UI and the `/login` $\leftrightarrow$ `/profile` redirect loop).
  - Configure `staleTime: 30_000` (30 seconds) on `useProfile()` instead of `0` so mounting `Navbar`, `ProfilePage`, and route guards within the same navigation does not fire 2–3 duplicate `GET /api/profile/` calls per page load, while mutations (`login`, `logout`, `updateProfile`) explicitly invalidate or set `["profile"]`.

## Capabilities

### New Capabilities
- `rate-limiting-and-auth-session-resilience`: Redis-backed rate-limiter configuration precedence, calibrated SPA/mobile default rate limits, CORS `OPTIONS` preflight exemption, and `useProfile()` resilience against HTTP `429` login lockout loops.

### Modified Capabilities
- None.

## Impact

- **Backend (`app/core/limiter.py`, `app/__init__.py`)**: Fixes `Flask-Limiter` storage resolution so Redis actually backs rate limiting in staging/production, emits standard `X-RateLimit-*` / `Retry-After` headers, exempts `OPTIONS` preflights, and raises default read/navigation limits to `1000 per hour; 10000 per day`.
- **Frontend (`frontend/lib/api/hooks/user.ts`)**: Eliminates false-logout and `/login` $\leftrightarrow$ `/profile` redirect loops on `429`/`5xx` responses and cuts redundant `/api/profile/` polling by 60–70% via `staleTime: 30_000`.
- **Tests**: Unit and integration tests in `tests/test_rate_limiting.py` and `frontend/__tests__/lib/api/hooks/user.test.ts`.
