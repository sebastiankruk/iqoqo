## Why

The multi-agent code review of PR #376 (`release/0.9.3` → `main`) identified five critical and four security/functional issues across TOTP 2FA & PAT authorization boundaries, missing `/login` 2FA UI challenge handling, cross-tenant SSE transition event leakage, and RDF export Item URI/privacy guards that must be resolved before tagging `v0.9.3`.

## What Changes

- **2FA & PAT Security Boundaries (`app/api/auth.py`, `app/api/decorators.py`, `app/db/auth.py`, `migrations/versions/v0_9_3_pats.py`)**:
  - Reject `POST /api/auth/2fa/enroll` when `user.totp_enabled` is already `True` unless disabled first, preventing unauthenticated overwrite of active TOTP secrets and recovery codes.
  - Reject Personal Access Token (`iqo_*`) authentication on `/api/auth/tokens*` and `/api/auth/2fa/*` (`403 Forbidden`), preventing PAT self-escalation or 2FA tampering.
  - Validate in `POST /api/auth/tokens` that callers cannot request `"admin"` or `"*"` scopes unless the user holds the `"admin"` role, nor request `PermissionName` scopes the user lacks; validate positive `expires_in_days` and safe `limit`/`offset` bounds in `GET /api/auth/tokens`.
  - Enforce PAT scope checks in `@admin_required` (`"admin"` or `"*"` required when `g.pat` is present) and `@admin_or_custodian_required`, closing the `GET` read-only PAT scope bypass on admin routes.
  - Restrict `?token=` query-string credential extraction in `_extract_bearer_token()` strictly to `/api/v1/events/stream`, add `@limiter.limit("10 per minute")` to `/api/auth/2fa/verify` and `/api/auth/2fa/disable`, throttle `pat.last_used_at` commits to 60-second intervals, and make `token_hash` index unique.
- **Frontend `/login` 2FA Challenge Step & E2E Coverage (`frontend/app/login/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`, `frontend/__tests__/e2e/pat_and_totp_workflow.spec.ts`)**:
  - Update `LoginPageContent` to handle `{"mfa_required": true}` from `POST /api/auth/login` by rendering the 6-digit TOTP / 8-character recovery code step and submitting `otp_code`.
  - Add localized `Login` strings in `en.json` and `pl.json` and add the `pat_and_totp_workflow.spec.ts` Playwright E2E test.
- **Per-User SSE Event Isolation, Redis Cleanup & Query Keys (`app/core/events.py`, `app/api/events.py`, `app/api/items.py`, `frontend/components/providers.tsx`, `frontend/__tests__/components/transition-events-listener.test.tsx`)**:
  - Scope `subscribe_events(user_id=g.user_id, ...)` so private user transitions (`item_created`, `item_updated`, `item_deleted`, `custody_lent`, `custody_returned`) are delivered only to the item owner or borrower.
  - Clamp SSE `timeout` to `[1.0, 60.0]` seconds with `math.isfinite` validation, close Redis clients in `finally` blocks, and wire `enqueue_fts_reindex` + `publish_transition_event` into `POST /api/item/<isbn>` (`add_item`).
  - Update `TransitionEventsListener` to invalidate `["facetStats"]`, `["globalStats"]`, `["collectionGrid"]`, `["items"]`, `["manifestations"]`, and `["stats"]`, and use `vi.spyOn(queryClient, "invalidateQueries")` in its unit test.
- **RDF Subject URI Alignment, Privacy Guards & Collection Scope Fix (`app/core/export_service.py`, `app/api/public_rdf.py`, `app/api/system.py`, `frontend/app/collection/page.tsx`, `docs/CHANGELOG.md`)**:
  - Fix `ExportService.build_batch_rdf_graph` to use plural `{base_url}/items/{item.id}`, read `item.borrower`, and require `not item.is_hidden and item.visibility != "private"` and `holder.visibility == "public"` before emitting `iqoqo:custodyHolder`.
  - Batch-load friends and filter out private profiles (`User.visibility != "private"` in `ExportService.export_rdf`; `User.visibility == "public"` in `get_public_user_followers`).
  - Preserve `"all"` / `"global"` scope on `frontend/app/collection/page.tsx` for logged-in users, restrict `GET /api/system/status?probe=true` remote OAuth probing to admins, and finalize `docs/CHANGELOG.md` and `0.9.x-release-plan.md`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `auth-pat-and-totp`: Enforce 2FA re-enrollment protection, reject PATs on token/2FA management endpoints, enforce PAT scopes on `@admin_required` / `@admin_or_custodian_required`, and add the `/login` 2FA challenge UI.
- `async-transitions-fts-indexing`: Scope SSE transition events per user, clamp SSE timeout and close Redis clients, emit transitions on `POST /api/item/<isbn>`, and align invalidated TanStack Query keys.
- `social-activitystreams-ontology`: Align `iqoqo:custodyHolder` subject URI to `/items/{id}`, use `item.borrower`, and enforce item/user visibility guards in `ExportService` and `get_public_user_followers`.
- `faceted-navigation`: Preserve `"all"` / `"global"` facet scope on the Collection page for authenticated users.

## Impact

- **Backend (`app/`)**: `app/api/auth.py`, `app/api/decorators.py`, `app/db/auth.py`, `migrations/versions/v0_9_3_pats.py`, `app/core/events.py`, `app/api/events.py`, `app/api/items.py`, `app/core/export_service.py`, `app/api/public_rdf.py`, `app/api/system.py`, `app/utils/igdb.py`
- **Frontend (`frontend/`)**: `frontend/app/login/page.tsx`, `frontend/app/collection/page.tsx`, `frontend/components/providers.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- **Tests & Docs**: `tests/test_auth_pat_and_totp.py`, `tests/test_sse_events.py`, `tests/test_rdf_serialization.py`, `frontend/__tests__/components/transition-events-listener.test.tsx`, `frontend/__tests__/e2e/pat_and_totp_workflow.spec.ts`, `docs/CHANGELOG.md`
