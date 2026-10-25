## 1. 2FA & Personal Access Token Security Boundaries

- [x] 1.1 In `app/api/auth.py`, reject `POST /api/auth/2fa/enroll` (`400`) when `user.totp_enabled` is already `True`, reject PAT authentication (`getattr(g, "pat", None) is not None` -> `403`) on `/api/auth/2fa/*` and `/api/auth/tokens*`, add `@limiter.limit("10 per minute")` to `/2fa/verify` and `/2fa/disable`, validate caller role/permissions before allowing `"admin"`, `"*"`, or `PermissionName` scopes in `create_token`, and validate `limit`/`offset` and `expires_in_days > 0`
- [x] 1.2 In `app/api/decorators.py`, enforce PAT scope checks in `@admin_required` (`"admin"` or `"*"` in `g.pat_scopes`) and `@admin_or_custodian_required`, restrict `?token=` query-string extraction in `_extract_bearer_token()` strictly to `request.path == "/api/v1/events/stream"`, throttle `pat.last_used_at` commits to 60-second intervals, and set `unique=True` on `token_hash` in `app/db/auth.py` and `migrations/versions/v0_9_3_pats.py`
- [x] 1.3 Expand `tests/test_auth_pat_and_totp.py` to test 2FA re-enrollment rejection, PAT rejection on `/api/auth/tokens` and `/api/auth/2fa/enroll`, non-admin `"admin"` scope rejection, and `read:catalog` PAT rejection on `@admin_required` `GET` routes

## 2. Frontend `/login` 2FA Challenge UI & E2E Test

- [x] 2.1 Update `frontend/app/login/page.tsx` and `frontend/messages/{en,pl}.json` to handle `{"mfa_required": true}` from `POST /api/auth/login` by rendering the 6-digit TOTP / recovery code input step and submitting `{ email, password, otp_code }`
- [x] 2.2 Add unit/integration test coverage in `frontend/__tests__/components/profile/pat-and-totp.test.tsx` (or login test) and author `frontend/__tests__/e2e/pat_and_totp_workflow.spec.ts`

## 3. Per-User SSE Event Isolation, Redis Cleanup & Query Keys

- [x] 3.1 Update `app/core/events.py`, `app/api/events.py`, `app/api/items.py`, and `app/api/lending.py` to filter user-specific SSE events by `user_id`, include `owner_id` on lending events, wire `enqueue_fts_reindex` and `publish_transition_event` into `POST /api/item/<isbn>` (`add_item`), clamp `timeout` to `[1.0, 60.0]` seconds with `math.isfinite`, and close Redis clients in `finally` blocks
- [x] 3.2 Update `TransitionEventsListener` in `frontend/components/providers.tsx` to invalidate `["facetStats"]`, `["globalStats"]`, `["collectionGrid"]`, `["items"]`, `["manifestations"]`, and `["stats"]`, and update `frontend/__tests__/components/transition-events-listener.test.tsx` and `tests/test_sse_events.py`

## 4. RDF Subject URI Alignment, Privacy Guards & Collection Scope Fix

- [x] 4.1 In `app/core/export_service.py` and `app/api/public_rdf.py`, change `/item/{item.id}` to `/items/{item.id}`, use `getattr(item, "borrower", None)`, guard `iqoqo:custodyHolder` on non-hidden/non-private items and `holder.visibility == "public"`, batch-load friends in `export_rdf` excluding `private` users, and filter `User.visibility == "public"` in `get_public_user_followers`; update `tests/test_rdf_serialization.py`
- [x] 4.2 Fix `frontend/app/collection/page.tsx` so `currentScope === "all" || currentScope === "global"` maps to `"global"` in `filtersForFacets` and `facetStatsScope`, restrict `probe_remote=True` in `GET /api/system/status` (`app/api/system.py`) to admins with sanitized error messages, and update `docs/CHANGELOG.md` and `.context/notes/plan/0.9.x-release-plan.md`
