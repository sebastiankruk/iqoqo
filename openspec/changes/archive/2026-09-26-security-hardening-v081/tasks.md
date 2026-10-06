## 1. High-Priority Authentication & Input Sanitization

- [x] 1.1 Enforce minimum password length (>= 8 characters) in `app/api/auth.py` registration and update endpoints, and verify with pytest in `tests/test_auth_security.py`
- [x] 1.2 Replace naive regex tag stripping in `_sanitize_text` with `bleach.clean(tags=[], attributes={}, protocols=[], strip=True)` in `app/api/social.py`, and verify with XSS injection test vectors in `tests/test_social_feedback.py`
- [x] 1.3 Validate `avatar_url` protocol against `https://` allowlist and block internal SSRF IP ranges in `app/api/profile.py`, and verify with `tests/test_api_security_hardening.py`

> `MOD-SEC-22` (account-deletion confirmation) is deferred to `account-deletion-email-confirmation-v083`, targeted for v0.8.3; it is intentionally not part of this task list.

## 2. Database Constraints & Schema Integrity

- [x] 2.1 Add `CheckConstraint("visibility IN ('private', 'shared', 'public')", name="check_user_visibility")` to `User` model in `app/db/auth.py`, and verify with model test
- [x] 2.2 Add `CheckConstraint` for `Item.status` and `Item.collection_status` in `app/db/core.py`, and verify with database rejection test
- [x] 2.3 Add `CheckConstraint` for `UserWorkIntent.status` in `app/db/core.py`, and verify with intent creation test
- [x] 2.4 Add a PostgreSQL trigger for the cross-table self-borrow invariant, retain API validation with a clear error, hide/disable the owner action in the lending UI, and verify database, API, and frontend behavior
- [x] 2.5 Verify existing `check_roadmap_item_single_frbr_level` enforces exactly one Work, Expression, or Manifestation target, preserving expression-only targets; do not add Item-level targeting in this change; verify with roadmap model/database tests
- [x] 2.6 Add `CheckConstraint("aggregated_type IN ('work', 'item')", name="check_container_aggregation_type")` in `app/db/games.py`, and verify with aggregation test
- [x] 2.7 Add `CheckConstraint("password_hash IS NOT NULL OR google_id IS NOT NULL", name="check_user_auth_method")` to `User` model in `app/db/auth.py`, and verify with constraint test
- [x] 2.8 Create and run Alembic migration for the new user visibility/auth-method and container aggregation constraints; preserve existing item, intent, and roadmap checks; verify migration upgrade and downgrade in `tests/test_migration.py`

## 3. Rate Limiting & Token Revocation Performance

- [x] 3.1 Implement two-tier Redis-cached token revocation lookup with PostgreSQL fallback in `app/api/decorators.py`, and verify with cache hit/miss tests in `tests/test_auth_security.py`
- [x] 3.2 Apply `@limiter.limit("60 per minute")` on `/api/public/feed.xml` and `@limiter.limit("30 per minute")` on `/api/profile/search`, and verify 429 response in `tests/test_api_security_hardening.py`
- [x] 3.3 Apply `@limiter.limit("30 per minute")` on collection share creation in `app/api/sharing.py`, and verify rate limiting test in `tests/test_api_security_hardening.py`
- [x] 3.4 Apply `@limiter.limit("30 per minute")` and document public aggregate-only access expectations on the existing `/api/stats/global` route in `app/api/system.py`; sanitize failures and verify rate limiting/error responses
- [x] 3.5 Add `@optional_auth` to `get_social_feedback` and `get_social_notes` in `app/api/social.py`, and verify response behavior for authenticated and anonymous callers

## 4. API & Query Injection Defenses

- [x] 4.1 Validate schema prefix against strict allowlist `('_CATALOG', '_INVENTORY')` in `app/core/search_service.py`, and verify that unexpected schema inputs fail closed
- [x] 4.2 Replace JWT-in-URL redirect with one-time authorization code exchange via POST in `app/api/auth.py` and `frontend/app/auth/exchange/route.ts`, verifying with auth flow tests
- [x] 4.3 Sanitize OAuth error messages in `app/api/auth.py` to prevent internal system information disclosure, and verify sanitized error response in test suite
- [x] 4.4 Strip raw ISBN input values and internal exception details from error responses in `app/api/manifestations.py`, and verify error payload test
- [x] 4.5 Fix IGDB query builder payload injection by escaping backslashes prior to quotes in `app/utils/igdb.py`, and verify sanitization with query injection unit tests
- [x] 4.6 Audit list-view route handlers in `app/api/works.py` and `app/api/manifestations.py` to ensure eager loading of `Manifestation.author` and `Work.expressions`, and verify query count assertions

## 5. Deployment, Environment & Operational Script Security

- [x] 5.1 Enforce `0o600` file permissions via `os.open` when writing cached IGDB tokens in `app/utils/igdb.py`, and verify file mode in filesystem test
- [x] 5.2 Update `frontend/app/share/[token]/page.tsx` to differentiate HTTP 404 from HTTP 50x error states, and verify UI rendering in Vitest component test
- [x] 5.3 Preserve the active Next.js 16 `frontend/proxy.ts` and its redirect tests; remove the deprecated `runtime = "edge"` export from `frontend/app/apple-icon.tsx` (Node.js is the default), then verify build/startup output has no Edge Runtime deprecation warning and `/apple-icon` still renders a PNG
- [x] 5.4 Update `docker-compose.yml` to remove default `POSTGRES_PASSWORD=changeme` and require explicit environment variable, and verify configuration parse test
- [x] 5.5 Verify the existing import-time `Config` validation in `app/config.py` rejects default/placeholder or weak `SECRET_KEY` values during production startup; add subprocess regression tests in `tests/test_config_service.py` for rejection and a strong key, without duplicating checks in `app/core/config_service.py`
- [x] 5.6 Set `ALLOW_LLM=false` by default in `.env.example`, and verify synchronization test in `tests/bash/env_example_sync.bats`
- [x] 5.7 Add non-empty, strong password validation in `scripts/init_auth.py`, and verify script rejects weak inputs
- [x] 5.8 Verify `user.is_active` status in `scripts/generate_admin_token.py` before issuing administrative tokens, and verify test with deactivated user

## 6. Integration & Verification

- [x] 6.1 Execute the full security test suite (`pytest tests/test_auth_security.py tests/test_admin_security.py tests/test_api_security_hardening.py`) and verify all tests pass cleanly
- [x] 6.2 Execute backend test suite (`make test-backend`) and verify zero regressions across all 29 in-scope MOD-SEC finding areas
> Verification status: `make test-backend` exited successfully: 1,946 passed, 4 skipped, 8 xpassed (569.52 seconds). The prior hundreds of failures/errors were caused by credential-less synthetic `User` fixtures violating `check_user_auth_method`; the test harness now gives synthetic test users unique test-only OAuth identities, while the dedicated negative constraint test opts out and still verifies database rejection. The initial full run also exposed stale generated taxonomy output; the generator refreshed it and both repeat/full runs passed. No developer database reset was performed.
- [x] 6.3 Execute frontend test suite (`npm --prefix frontend test`) and verify zero test regressions
