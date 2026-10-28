## Context

See `proposal.md` for motivation. Live multi-instance testing between `preview.iqoqo.cc` and `peer.iqoqo.cc` exposed five interconnected issues across admin trust management, user privacy settings, ActivityPub task execution, federated handle resolution, and profile visibility persistence:

1. **4-Tier Trust Confusion**: `TrustLevel` currently exposes `untrusted`, `pending`, `trusted`, and `blocked`, and `federation-instances.tsx` renders both a status badge (`"Pending Review"`) and a `<select>` dropdown in the same table cell. Administrators read `"Pending Review"` as meaning the peer connection itself is awaiting approval, and `untrusted` vs `pending` have identical behavior for social/friend requests.
2. **Global vs Per-User Follow Auto-Acceptance**: `FEDERATION_AUTO_ACCEPT_FOLLOWS` was placed in the global Admin Federation Settings card (`instance-settings.tsx`), whereas deciding whether incoming friend/follow requests are auto-accepted or require manual approval is a personal user privacy choice that belongs on `/profile` (`FederationConsentSettings`).
3. **Navbar "Public Profile" 404**: `navbar.tsx` renders a `"Public Profile"` link (`/u/${profile.public_username}`) whenever `public_username` is set, even when `profile.visibility` is `private` or `friends_only`. Furthermore, `frontend/app/u/[username]/page.tsx` performs server-side `fetch()` calls without forwarding the caller's `cookie` header, causing `/api/public/u/<username>` to treat every SSR request as anonymous (`viewer_id = None`) and return 404 for `friends_only` and owner-viewed `private` profiles.
4. **Celery Result-Backend `RuntimeError` & `@` Handle Parsing in Friend Requests**:
   - In `docker-compose.federation-preview.yml`, `peer-web` runs without a local Redis container (`REDIS_URL` defaults to `redis://localhost:6379/0`) and without a dedicated `peer-worker` (sharing `iqoqo-preview-worker-1` would point tasks at `preview-db` instead of `peer-db`). When `receive_inbox` or `dispatch_follow` calls `submit_task`, Celery's Redis result backend (`self.backend.on_task_call`) retries `localhost:6379` 20 times (20 seconds) and raises `RuntimeError("Retry limit exceeded while trying to reconnect to the Celery result store backend")`. Because `submit_task` (`app/core/tasks.py`) only caught `(KombuError, OSError)`, the uncaught `RuntimeError` aborted `receive_inbox` with HTTP 500 before `if not task_id: process_inbound_activity(...)` could run!
   - In `send_friend_request` (`app/core/friend_service.py`) and `_handle_webfinger_lookup` (`app/api/federation.py`), `.split("@", 1)` split on the *first* `@`, turning `peer-admin@iqoqo.cc@peer.iqoqo.cc` into `username="peer-admin"` and `domain="iqoqo.cc@peer.iqoqo.cc"`. Additionally, `_handle_webfinger_lookup` only checked `User.public_username == username` (never `User.email`), and `send_friend_request` did not check registered `FederationInstance` peers when a user entered `peer-admin@iqoqo.cc` (where the email domain `iqoqo.cc` differs from the peer host `peer.iqoqo.cc`).
5. **`PUT /api/profile/` Visibility Validation**: `update_profile` (`PUT /api/profile/` in `app/api/profile.py`) restricted `visibility` and `default_item_visibility` to `["public", "private"]`, rejecting `"friends_only"` with HTTP 400 (`"Invalid default_item_visibility. Must be 'public' or 'private'"`).

## Goals / Non-Goals

**Goals:**
- Consolidate peer trust in the UI and sync pipeline into 3 clear categories (`trusted`, `untrusted`, `blocked`) where `untrusted` merges with `pending` (routing incoming catalog metadata proposals to the Custodian Provider Merge Queue while allowing social friend/collection requests).
- Remove the redundant trust status pill in `federation-instances.tsx`, remove `FEDERATION_AUTO_ACCEPT_FOLLOWS` and `FEDERATION_DEFAULT_TRUST` from `instance-settings.tsx`, and provide a plain-language guide to unilateral peering and the 3 trust levels.
- Move `auto_accept_follows` to per-user `FederationConsentSettings` on `/profile`, backed by `ConsentRecord` (`consent_type="federation_auto_accept_follows"`) with zero database schema migrations.
- Remove the 404-prone `"Public Profile"` item from `navbar.tsx` and forward request cookies in `frontend/app/u/[username]/page.tsx`.
- Make `submit_task` fail fast (<50ms) and catch all broker/backend exceptions (`RuntimeError`, `RedisError`, `Exception`) so synchronous fallback (`process_inbound_activity` and `deliver_activity`) always executes when Redis is unreachable, and set `CELERY_TASK_ALWAYS_EAGER=true` on `peer-web` in `docker-compose.federation-preview.yml`.
- Support `@username@peer`, `@email@peer`, and `email` (across registered peer instances) in `send_friend_request` and `_handle_webfinger_lookup`.
- Allow `"friends_only"` and `"shared"` in `PUT /api/profile/` for `visibility` and `default_item_visibility`.

**Non-Goals:**
- Introducing new Alembic database migrations (the single linear migration head `v0_9_3_pats` is preserved).
- Automatic bidirectional S2S trust negotiation (ActivityPub trust remains under each instance administrator's control).

## Decisions

### 1. 3-Category Trust Model (`trusted`, `untrusted`, `blocked`) Merging `untrusted = pending`
- **Decision**:
  - In `frontend/components/admin/federation-instances.tsx`, set `TRUST_LEVELS = ["untrusted", "trusted", "blocked"]`, normalize any legacy `"pending"` instance value to `"untrusted"` in the `<select>` value (`inst.trust_level === "pending" ? "untrusted" : inst.trust_level`), and remove `getTrustBadge(inst.trust_level, t)` from the table cell so only the `<select>` dropdown is rendered.
  - In `app/core/federation_sync.py` (`sync_manifestation`), route both `TrustLevel.UNTRUSTED` and legacy `TrustLevel.PENDING` into the Custodian Provider Merge Queue (`raw_payload[f"federation:{domain}"]` + `EntityAuditLog(change_type="federation_merge_proposed")`), while only `TrustLevel.BLOCKED` is discarded at the border and `TrustLevel.TRUSTED` auto-fills empty local fields.
  - In `app/core/federation_discovery.py` (`get_safe_default_trust`), default newly discovered peers to `TrustLevel.UNTRUSTED` (`"untrusted"`). Keep `"pending"` in `TrustLevel.ALL` on the backend as a legacy alias mapped/accepted for backward compatibility with existing DB rows and tests, while the UI presents the 3 categories (`Trusted`, `Untrusted`, `Blocked`).
  - Remove `FEDERATION_AUTO_ACCEPT_FOLLOWS` and `FEDERATION_DEFAULT_TRUST` from `SETTING_GROUPS.federation` in `frontend/components/admin/instance-settings.tsx`.
- **Rationale**: Eliminates the confusing split between `untrusted` and `pending` while preserving the safe Custodian Review Queue workflow for non-trusted peers and keeping 100% backward compatibility with existing database rows.

### 2. Per-User `auto_accept_follows` via `ConsentRecord`
- **Decision**:
  - In `app/api/profile.py` (`_handle_get_federation_consent` and `_handle_update_federation_consent`), read and write a `ConsentRecord` row with `consent_type="federation_auto_accept_follows"` for the current user, and include `"auto_accept_follows": bool` in the JSON payload returned by `/api/v1/profile/federation-consent` (and `/api/profile/federation-consent`).
  - In `frontend/components/settings/federation-consent.tsx`, add a third checkbox toggle (`id="toggle-fed-auto-accept"`) for `auto_accept_follows` with localized title and description in `en.json` and `pl.json`.
  - In `app/core/federation_handlers.py` (`handle_follow`), check whether the target user has `ConsentRecord(user_id=user.id, consent_type="federation_auto_accept_follows", is_granted=True)` (while also honoring legacy `FEDERATION_AUTO_ACCEPT_FOLLOWS=True` + `TrustLevel.TRUSTED` if explicitly set in config/env so existing backend unit tests remain compatible). When the user has `auto_accept_follows=True` and the peer instance is not `BLOCKED`, `handle_follow` immediately sets `FollowStatus.ACCEPTED` and dispatches `Accept(Follow)`.
  - Similarly, in `app/core/friend_service.py` (`send_friend_request` for local users), if `target_user` has `auto_accept_follows=True`, immediately set `UserFriendship.status = "accepted"`.
- **Rationale**: Puts friend/follow auto-acceptance under each user's personal control without requiring an Alembic schema migration on `federation.federation_consents`.

### 3. Fail-Fast Celery/Redis Fallback & `peer-web` Eager Execution
- **Decision**:
  - In `app/core/celery_app.py`, add `broker_transport_options={"max_retries": 0, "socket_connect_timeout": 1, "socket_timeout": 1}` and `result_backend_transport_options={"max_retries": 0, "socket_connect_timeout": 1, "socket_timeout": 1, "retry_policy": {"max_retries": 0}}`, and support `task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes")`.
  - In `app/core/tasks.py` (`submit_task`), if `celery.conf.task_always_eager` is `True`, return `None` (so callers execute the function directly in-process), and widen `except (KombuError, OSError):` to `except Exception as exc:` so `RuntimeError` from `celery.backends.asynchronous` or `redis.exceptions.RedisError` never crashes an HTTP request and always triggers the caller's `if not task_id:` synchronous fallback!
  - In `docker-compose.federation-preview.yml`, set `CELERY_TASK_ALWAYS_EAGER=true` on `peer-web` so `peer-web` processes inbound/outbound ActivityPub tasks synchronously against `peer-db` without hanging on `localhost:6379` or routing tasks to `preview-worker`.
- **Rationale**: Prevents 20-second Gunicorn hangs and HTTP 500 crashes when Redis is down or unconfigured on a peer container.

### 4. Right-Split (`rsplit("@", 1)`) Handle Parsing & Registered-Peer Email Discovery
- **Decision**:
  - In `app/api/federation.py` (`_handle_webfinger_lookup`), replace `account_part.split("@", 1)` with `account_part.rsplit("@", 1)` when the right side matches an allowed local host (`domain`, `req_host`), and if the right side does NOT match the local host (e.g. `acct:peer-admin@iqoqo.cc` queried directly against `peer.iqoqo.cc`), treat the full `account_part` (`peer-admin@iqoqo.cc`) as the lookup identifier! Look up the user by case-insensitive `User.public_username`, case-insensitive `User.email`, UUID, or (if unique) the local-part of `User.email` before `@`.
  - In `app/core/friend_service.py` (`send_friend_request`), parse `@` handles using `clean_id.lstrip("@").rsplit("@", 1)`. If WebFinger on `target_domain` fails (for instance, when the user typed an email `peer-admin@iqoqo.cc` where `target_domain="iqoqo.cc"` is an email domain rather than the peer host `peer.iqoqo.cc`), iterate over registered non-blocked `FederationInstance` domains and query WebFinger on each peer (`acct:{clean_id.lstrip('@')}@{peer.domain}` and `acct:{target_username}@{peer.domain}`).
- **Rationale**: Allows users to add federated friends seamlessly using `@peeradmin@peer.iqoqo.cc`, `peer-admin@iqoqo.cc@peer.iqoqo.cc`, or `peer-admin@iqoqo.cc` (when `peer.iqoqo.cc` is a connected peer).

## Risks / Trade-offs

- **[Risk] Searching registered peers by email on friend request could probe multiple peers** → **Mitigation**: Only fallback-probe registered non-blocked `FederationInstance` records (bounded to at most 5 recently seen peers with a short `3.0s` timeout) when direct WebFinger on `target_domain` does not resolve an actor.
- **[Risk] Legacy tests asserting `TrustLevel.PENDING` in backend unit suites** → **Mitigation**: Keep `TrustLevel.PENDING = "pending"` as a valid constant in `app/db/federation.py` and treat both `UNTRUSTED` and `PENDING` identically in `sync_manifestation` (routing to the Custodian Review Queue), while normalizing UI options to the 3 categories (`trusted`, `untrusted`, `blocked`).
