## 1. Backend Rate-Limiter Storage, Headers, Limits & OPTIONS Exemption

- [x] 1.1 In `app/core/limiter.py`, update `default_limits` to `["1000 per hour", "10000 per day"]`, remove `storage_uri="memory://"` from the `Limiter(...)` constructor so `app.config["RATELIMIT_STORAGE_URI"]` takes effect in `limiter.init_app(app)`, and register a `@limiter.request_filter` exempting `request.method == "OPTIONS"`.
- [x] 1.2 In `app/__init__.py`, set `app.config.setdefault("RATELIMIT_HEADERS_ENABLED", True)` before `limiter.init_app(app)` so `X-RateLimit-*` and `Retry-After` headers are emitted.

## 2. Frontend `useProfile()` 429 Resilience & Polling Reduction

- [x] 2.1 In `frontend/lib/api/hooks/user.ts`, update `useProfile()` so only `401`/`403`/`404` responses return `null` (with `clearAuthToken()` on `401`), while `429`/`5xx`/network errors return `getCachedProfileSnapshot()` if available or rethrow the error instead of returning `null`; set `staleTime: 30_000` and disable immediate retry on `401`/`403`/`404`/`429`.

## 3. Regression Tests & Verification

- [x] 3.1 Add backend tests in `tests/test_rate_limiting.py` verifying that `limiter._storage_uri` does not override `app.config["RATELIMIT_STORAGE_URI"]`, `RATELIMIT_HEADERS_ENABLED` emits `X-RateLimit-*` headers, `default_limits` allow $>50$ requests/hour (`1000 per hour`, `10000 per day`), and `OPTIONS` preflight requests are exempt from rate-limit counters.
- [x] 3.2 Add frontend unit tests in `frontend/__tests__/lib/api/hooks/user.test.ts` verifying `useProfile()` behavior on `401` (clears token and returns `null`), `429` with cached snapshot (returns cached profile), and `429` without cached snapshot (throws error rather than returning `null`).
