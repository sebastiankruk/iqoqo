## 1. Rate Limit Implementation (MOD-1)

- [x] 1.1 Add `@limiter.limit("60/minute")` to read endpoints in `app/api/public_items.py`, `app/api/public_profile.py`, `app/api/lending.py`, `app/api/roadmap.py` and verify rate limit headers are present in local testing.
- [x] 1.2 Add `@limiter.limit("30/minute")` to write endpoints in the same files and verify 429 errors are triggered when limits are exceeded.
- [x] 1.3 Add test case asserting rate limits on public endpoints to `test_api_security_hardening.py` and verify it passes.

## 2. Query Optimization (MOD-2 & MOD-3)

- [x] 2.1 Update Admin User List query in `app/api/admin.py` to use `.options(selectinload(User.roles))` and `.options(selectinload(Role.permissions))` and verify query count reduction via test or logs.
- [x] 2.2 Update FRBR Service RDF Enrichment queries in `app/core/frbr_service.py` to use `.options(joinedload(cls.contributor))` and verify serialization succeeds without generating excessive queries.

## 3. Remove Public Module Shim (MOD-7)

- [x] 3.1 Run codebase-wide find-and-replace to update `app.api.public` imports to `app.api.public_items`, `app.api.public_profile`, `app.api.public_rdf`. Verify tests still pass.
- [x] 3.2 Delete `_PublicModuleShim` from `app/api/public.py` and verify `pytest` suite passes with no import errors.

## 4. Input Validation (MOD-13 & MOD-14)

- [x] 4.1 Update OAuth callback logic in `app/api/auth.py` to validate `avatar_url` (check HTTPS and safety), falling back to None if invalid, and verify via test with malicious URL.
- [x] 4.2 Update `update_profile` in `app/api/profile.py` to enforce a 500-character bio limit, returning 400 if exceeded, and verify via test with oversized bio string.

## 5. FRBR Editor Caching (CRIT-7)

- [x] 5.1 Update `frontend/components/admin/frbr-editor.tsx` to replace `setLastFetched(Date.now())` with `onMutate`/`onSettled` cache updates using `queryClient.setQueryData`. Verify UI updates without jarring remounts.
- [x] 5.2 Update `relation-management-dialog.tsx` to use targeted `queryClient.setQueryData` instead of global `invalidateQueries()`. Verify cache state remains consistent.
