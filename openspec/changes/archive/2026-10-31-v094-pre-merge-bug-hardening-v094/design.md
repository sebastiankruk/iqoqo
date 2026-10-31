# Design: v094-pre-merge-bug-hardening-v094

## Architecture & Technical Decisions

### 1. Inbound Activity Query Scoping (`friend_service.py`)
In `list_friends()` and `respond_friend_request()`:
- Pending inbound activities must be scoped by querying `FederationActivity` where `actor_uri.in_(pending_actor_uris)`.
- In addition, inbound activities must be validated to ensure the target is the local user:
  - Check `act.target_uri == local_actor_iri` or `act.object_json.get("object") == local_actor_iri` (or contains the user's UUID).
- This prevents a local user from adopting or self-approving a follow sent by the same remote actor to a *different* local user on the same multi-tenant instance.

### 2. ActivityPub Outbound `Reject(Follow)` and `Undo(Follow)`
In `friend_service.py`:
- When a user rejects an inbound follow (`action == "reject"` on `fed:<id>`), dispatch `Reject(Follow)` via `federation_dispatch.dispatch_activity` or outbound activity delivery to the follower's inbox.
- When a user removes or cancels an active federated friend (`remove_friend()`), construct and deliver an `Undo(Follow)` activity targeting the remote actor's inbox so both instances remain synchronized.

### 3. WebFinger Wildcard Sanitization and Query Fallback
In `app/api/federation.py` and `app/core/friend_service.py`:
- In `_handle_webfinger_lookup()`, eliminate `ilike(f"{username}@%")` with unescaped wildcards. Use explicit equality matches:
  1. `func.lower(User.public_username) == username.lower()`
  2. `func.lower(User.email) == username.lower()`
  3. `func.split_part(func.lower(User.email), '@', 1) == username.lower()`
- In fallback discovery in `send_friend_request()`, order candidate instances by `last_seen_at.desc().nullslast()`, limit to 5, and append `@{instance.domain}` to the `acct:` query resource to avoid remote 404 domain mismatch errors.

### 4. Anchored Actor IRI Verification & Notification Action Cleanliness
In `app/core/federation_handlers.py` and `frontend/components/dashboard/notification-center.tsx`:
- Validate that `actor_uri.rstrip("/").endswith(f"/u/{target_id}")` or regex-anchored UUID matching is satisfied.
- In `handle_follow`, ensure that auto-accepted follows set `target_iri = "/profile?tab=accepted#friends"`.
- In `notification-center.tsx`, verify `payload?.status !== "accepted"` before rendering inline Accept/Reject buttons.

### 5. Frontend E2E Placeholder Update
Update placeholder regex in `frontend/__tests__/e2e/federation_pair_live.spec.ts` and `frontend/__tests__/e2e/federation_matrix_workflows.spec.ts` to match `library.example.org|biblioteka.example.org`.

### 6. Low Priority Hardening Fixes
- `friend_service.py` & `profile.py`: Normalize `target_domain = clean_instance_domain(target_domain)` before checking block status. Check `get_actor_public_key()` before generating RSA keypairs. Preserve `federated_collection` when updating profile federation consent.
- `federation_keys.py`: Call `db.session.rollback()` in `sync_key_to_db` exception handler.
- `migrations/versions/v0_9_4_user_friends_only_checks.py`: In `downgrade()`, normalize existing `'friends_only'` and `'shared'` rows to `'public'` or `'private'` before adding narrower checks.
- `scripts/restore.sh`: Use `find ... -print0` with `while IFS= read -r -d ''` and `--no-same-owner` in tar.
- `docs/FEDERATION.md` & `docs/CHANGELOG.md`: Update documentation and changelog stamps.
