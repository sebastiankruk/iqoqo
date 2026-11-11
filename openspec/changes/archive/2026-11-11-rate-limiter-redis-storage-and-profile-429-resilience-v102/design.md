## Context

During production verification of `v1.0.1` on `iqoqo.kruk.cc` (`🪳 Prod Login Lockout — Rate Limiter Defect Stack.md`), a single active user testing the web SPA and Android Capacitor app was locked out of logging in and viewing `/profile` for the remainder of the hour. Investigation revealed four compounding defects across `app/core/limiter.py`, `app/__init__.py`, and `frontend/lib/api/hooks/user.ts`:

1. `app/core/limiter.py` sets `default_limits=["200 per day", "50 per hour"]`. Every route lacking an explicit `@limiter.limit` decorator (`GET /api/profile/`, `GET /api/items`, `GET /api/config`, etc.) shares this tiny budget.
2. `app/core/limiter.py` passes `storage_uri="memory://"` to `Limiter(...)`. In `flask-limiter 4.1.1`, `self._storage_uri` set in `__init__` takes precedence over `app.config["RATELIMIT_STORAGE_URI"]` in `init_app(app)`. Consequently, `app.config["RATELIMIT_STORAGE_URI"] = redis_url` in `app/__init__.py:253` was completely ignored in production, leaving counters trapped in each Gunicorn worker's heap memory.
3. Unauthenticated CORS `OPTIONS` preflights from the Capacitor WebView were counted against the IP rate-limit bucket.
4. `useProfile()` in `frontend/lib/api/hooks/user.ts` had `staleTime: 0` (triggering 2–3 `GET /api/profile/` fetches per page navigation) and caught all errors—including `429`—by returning `getCachedProfileSnapshot()`, which returns `null` on web browsers. Returning `null` caused the React tree to treat the user as logged out, while `frontend/proxy.ts` saw the valid `session` cookie and redirected `/login` back to `/profile` in an infinite loop.

## Goals / Non-Goals

**Goals:**
- Ensure `app.config["RATELIMIT_STORAGE_URI"]` (Redis in prod/preview, `memory://` fallback in dev/tests) actually controls `Flask-Limiter` storage.
- Emit standard `X-RateLimit-*` and `Retry-After` headers (`RATELIMIT_HEADERS_ENABLED = True`).
- Calibrate `default_limits` to `["1000 per hour", "10000 per day"]` while keeping strict per-route limits on auth, account mutations, user search, scanner, and federation routes.
- Exempt HTTP `OPTIONS` preflight requests from rate limiting.
- Prevent `useProfile()` from turning HTTP `429`/`5xx` into a false `null` (logged-out) state and reduce duplicate `/api/profile/` polling with `staleTime: 30_000`.

**Non-Goals:**
- Changing explicit `@limiter.limit` budgets on authentication (`/api/auth/login` `20/min`), scanner (`/api/scan` `10/min`), or federation routes.
- Modifying Next.js edge middleware (`frontend/proxy.ts`) cookie checks.

## Decisions

### Decision 1: Remove `storage_uri="memory://"` from `Limiter(...)` Constructor (`app/core/limiter.py`, `app/__init__.py`)
- **Choice**: Instantiate `limiter = Limiter(key_func=get_user_id_or_ip, default_limits=["1000 per hour", "10000 per day"])` without `storage_uri` in `app/core/limiter.py`. In `app/__init__.py`, ensure `app.config["RATELIMIT_STORAGE_URI"]` is always explicitly set (to `redis_url` when reachable, or `"memory://"` otherwise) and set `app.config.setdefault("RATELIMIT_HEADERS_ENABLED", True)` before `limiter.init_app(app)`.
- **Rationale**: `flask-limiter` resolves `storage_uri = self._storage_uri or app.config.get("RATELIMIT_STORAGE_URI") or "memory://"`. Leaving `self._storage_uri` as `None` lets `app.config["RATELIMIT_STORAGE_URI"]` work as designed while still defaulting to `"memory://"` if unconfigured.

### Decision 2: Exempt `OPTIONS` Preflights via `@limiter.request_filter` (`app/core/limiter.py`)
- **Choice**: Register a `@limiter.request_filter` function `exempt_options_preflight() -> bool` in `app/core/limiter.py` returning `request.method == "OPTIONS"`.
- **Rationale**: `@limiter.request_filter` in `Flask-Limiter` exempts matching requests from both `default_limits` and route-specific `@limiter.limit` decorators, ensuring CORS `OPTIONS` preflights never consume quota on any endpoint.

### Decision 3: Distinguish `401`/`404` from `429`/`5xx` in `useProfile()` and Set `staleTime: 30_000` (`frontend/lib/api/hooks/user.ts`)
- **Choice**:
  - In `useProfile()`, inspect `err?.status`:
    - If `status === 401 || status === 403 || status === 404`: clear native auth token on `401` and return `null` (genuinely unauthenticated).
    - Otherwise (e.g., `429`, `502`, `503`, or network timeout): check `getCachedProfileSnapshot()` first; if non-null, return the cached snapshot; if `null` (such as on web browsers where IndexedDB offline snapshots are empty), **rethrow `err`** instead of returning `null`.
  - Set `staleTime: 30_000` and `retry: (failureCount, error: any) => error?.status !== 401 && error?.status !== 403 && error?.status !== 404 && error?.status !== 429 && failureCount < 1`.
- **Rationale**: When `useProfile()` rethrows on `429` instead of returning `data: null`, TanStack Query keeps any previously fetched `profile` data in cache and surfaces `isError: true` rather than claiming the user is logged out (`data === null`), breaking the `/login` $\leftrightarrow$ `/profile` redirect loop. Avoiding immediate auto-retry on `429` also prevents hammering a rate-limited endpoint.

## Risks / Trade-offs

- **Risk**: Existing tests might expect `staleTime: 0` or test `useProfile()` error handling with generic errors.
  - **Mitigation**: Update and expand unit tests in `frontend/__tests__/lib/api/hooks/user.test.ts` to cover `401` (returns `null`), `429` with cached snapshot (returns snapshot), `429` without cached snapshot (rejects/throws instead of returning `null`), and verify all existing frontend test suites pass.
