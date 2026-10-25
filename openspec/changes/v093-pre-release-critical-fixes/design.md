## Context

PR #376 (`release/0.9.3` → `main`) consolidates the five v0.9.3 OpenSpec deliverables (`C83e`, `C84`, `C85`, `C86`, `C87`). Multi-perspective review by the Principal Code Reviewer and Gemini Argon uncovered five `CRITICAL` and four security/functional `MODERATE` findings that must be resolved before tagging `v0.9.3`:
1. Unprotected 2FA re-enrollment (`enroll_2fa` overwrites active secrets without verification), PAT self-escalation on `/api/auth/tokens*` and `/api/auth/2fa/*`, unvalidated `"admin"` / `"*"` PAT scope creation by non-admins, and `read:catalog` PAT bypass on `@admin_required` / `@admin_or_custodian_required` `GET` routes.
2. Missing 2FA challenge step in `frontend/app/login/page.tsx` when `POST /api/auth/login` returns `{"mfa_required": true}`.
3. Cross-tenant broadcast of private item/custody transition events over `GET /api/v1/events/stream`, unbounded SSE `timeout` parameter, unclosed Redis connections, missing `add_item` (`POST /api/item/<isbn>`) transition emission, and mismatched TanStack Query invalidation keys.
4. Singular `/item/{id}` vs plural `/items/{id}` URI drift on `iqoqo:custodyHolder`, `item.lent_to_user` vs `item.borrower` lookup bug, missing item/user visibility checks in `ExportService` and `get_public_user_followers`, `CollectionPage` `"all"` scope coercion to `"user"`, and non-admin remote OAuth probing on `GET /api/system/status?probe=true`.

## Goals / Non-Goals

**Goals:**
- Enforce strict privilege and session boundaries across TOTP 2FA and Personal Access Token (`iqo_*`) endpoints and decorators.
- Complete the `/login` 2FA challenge UI in `frontend/app/login/page.tsx` and E2E workflow coverage in `pat_and_totp_workflow.spec.ts`.
- Isolate user-specific SSE transition events per authenticated user (`user_id`), bound SSE timeouts and Redis client lifecycles, emit transitions on `POST /api/item/<isbn>`, and invalidate all relevant TanStack Query keys.
- Align `ExportService` Item URIs (`/items/{id}`), enforce item/borrower/friend visibility rules in `ExportService` and `public_rdf.py`, preserve `"all"` / `"global"` facet scope in `CollectionPage`, and restrict remote Twitch OAuth probing on `/api/system/status?probe=true` to admins.

**Non-Goals:**
- Non-blocking package/backoff refinements (`boardgamegeek2>=1.3`, `Retry-After` cap), Celery Redis `NX EX` debounce lock, OpenAPI component schema polish, and `TotpSetup`/`PatManagement` translation wiring (tracked in `v093-review-deferrals-v094` for `v0.9.4`).

## Decisions

1. **Session-Only Guard for Token & 2FA Management (`app/api/auth.py` & `app/api/decorators.py`)**:
   - Add a helper `_reject_pat_auth()` (or check `if getattr(g, "pat", None) is not None: return jsonify({"error": "Personal access tokens cannot manage tokens or 2FA settings"}), 403`) on `enroll_2fa`, `verify_2fa`, `disable_2fa`, `get_2fa_status`, `list_tokens`, `create_token`, and `revoke_token`.
   - In `enroll_2fa`, if `user.totp_enabled` is `True`, return `400 Bad Request` (`{"error": "2FA is already enabled. Disable 2FA before re-enrolling."}`).
   - In `create_token`, verify that `"admin"` or `"*"` scopes are only permitted if the user holds the `"admin"` role, and specific `PermissionName` scopes are only permitted if `user.has_permission(perm)`.
   - In `@admin_required` and `@admin_or_custodian_required`, when `getattr(g, "pat_scopes", None)` is not `None`, require `"admin"` or `"*"` in `g.pat_scopes` (or curator/admin scope for `@admin_or_custodian_required`).
   - Restrict `?token=` extraction in `_extract_bearer_token()` to `request.path == "/api/v1/events/stream"`.
2. **Per-User SSE Filtering (`app/core/events.py`, `app/api/events.py`, `app/api/lending.py`)**:
   - Include `user_id` (and `borrower_id` on custody events) in event payloads, and pass `user_id=str(g.user_id)` into `subscribe_events(timeout_seconds=timeout, user_id=str(g.user_id))`.
   - Filter events in `subscribe_events`: user-scoped events (`item_created`, `item_updated`, `item_deleted`, `custody_lent`, `custody_returned`) are yielded only when `str(user_id) in {str(data.get("user_id")), str(data.get("owner_id")), str(data.get("borrower_id"))}` (or when `user_id is None` in unit tests that call `subscribe_events` directly without a user filter).
3. **Canonical `/items/{id}` URI & Visibility Filtering in `ExportService` & `public_rdf.py`**:
   - Use `URIRef(f"{base_url}/items/{item.id}")` and `getattr(item, "borrower", None)` in `ExportService.build_batch_rdf_graph`, and require `not getattr(item, "is_hidden", False) and getattr(item, "visibility", "private") != "private"` and `getattr(holder, "visibility", "private") == "public"`.
   - Batch-load friends with `select(User).where(User.id.in_(friend_ids), User.visibility != "private")` in `ExportService.export_rdf` and `select(User).where(User.id.in_(local_friend_ids), User.visibility == "public")` in `get_public_user_followers`.

## Risks / Trade-offs

- **Existing unit tests calling `subscribe_events` without `user_id`**: Defaulting `user_id: str | None = None` in `subscribe_events` preserves backward compatibility for unit tests while `GET /api/v1/events/stream` always passes `user_id=str(g.user_id)`.
