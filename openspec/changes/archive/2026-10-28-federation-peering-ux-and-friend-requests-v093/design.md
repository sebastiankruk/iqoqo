## Context

See `proposal.md` for problem motivation and user observations.

In `iqoqo`, social relationships span both local (`UserFriendship`) and federated (`FederationFollower` / `FederationActor`) paradigms. Under the current `v0.9.3` release freeze, no database schema changes or Alembic migrations are permitted. The existing `FederationFollower` model contains only `(id, local_user_id, remote_actor_id, status, created_at)` without an explicit direction column.

However, the application already records all outbound and inbound ActivityStreams operations in `FederationActivity` (`direction="outbound"` vs `"inbound"`, `activity_type="Follow"`).

## Goals / Non-Goals

**Goals:**
- Reliably segregate pending federated friend requests into `outgoing` (for requester) and `incoming` (for recipient) in `list_friends(user_id)` without requiring database migrations.
- Block callers from accepting or rejecting outbound requests they initiated themselves in `respond_friend_request`.
- Clarify ActivityPub peering asymmetry and the roles of `FEDERATION_DEFAULT_TRUST` and `FEDERATION_AUTO_ACCEPT_FOLLOWS` in the `/admin/federation` UI.
- Protect all changes with targeted unit tests (backend `test_friend_service.py`, frontend `friends-card.test.tsx`) and an end-to-end integration test verifying the complete friend request cycle.

**Non-Goals:**
- Introducing database schema migrations to `federation_followers` (must remain at linear Alembic revision `v0_9_3_pats`).
- Altering standard W3C ActivityPub protocol semantics to force non-standard server-to-server peering handshakes.

## Decisions

### 1. Activity-Backed Follow Direction Determination
**Decision**: In `list_friends(user_id)`, for any `FederationFollower` where `status == FollowStatus.PENDING`, query whether an outbound `FederationActivity` exists where:
- `direction == "outbound"`
- `activity_type == "Follow"`
- `actor_uri == canonical_actor_iri(user_id)`
- `target_uri == remote_actor.inbox_url` (or `object_json["object"] == remote_actor.actor_uri`)

If a matching outbound activity exists, the record is placed into `outgoing`. If no outbound activity exists (i.e. it arrived via inbound inbox), it is placed into `incoming`.

*Alternatives considered*:
- Adding an `is_outbound` boolean column to `FederationFollower`: Rejected due to release freeze prohibiting schema migrations.
- Using a separate table for outbound follows: Rejected for the same reason.

### 2. Guarding `respond_friend_request`
**Decision**: In `respond_friend_request`, if `friendship_id` begins with `fed:`, perform the same outbound check before processing `accept` or `reject`. If the user is the sender of the outbound follow, reject the call with HTTP `400 Bad Request` (`"Cannot respond to an outgoing request you initiated; use cancel instead"`).

### 3. Reciprocal Peering UI Banner and Helper Tooltips
**Decision**: In `frontend/components/admin/federation-instances.tsx`, add an informative `Alert` callout explaining:
1. Peering is unilateral: adding an instance here verifies their public actor and records outbound trust locally.
2. For the remote instance to auto-accept activities and reciprocate trust, the remote administrator must also add this instance and assign `Trusted` status.
3. How `FEDERATION_DEFAULT_TRUST` and `FEDERATION_AUTO_ACCEPT_FOLLOWS` govern incoming activities from peers not yet marked as `Trusted`.

### 4. Federated Profile Consent Notice on Profile Friends Tab
**Decision**: In `frontend/components/profile/friends-card.tsx`, add a helper caption below the target user input explaining that federated users (`@user@domain`) must have enabled "Federated Profile" on their home instance to receive friend requests.

## Risks / Trade-offs

- **[Activity Log Retention]** If `FederationActivity` rows are aggressively purged or truncated by maintenance scripts, older pending requests might lack an activity record.
  → *Mitigation*: Fall back safely to `incoming`, and ensure `FederationActivity` rows for pending follows are retained until resolved (`ACCEPTED` or `REJECTED`).
- **[Asynchronous Failure Blindspot]** If delivery to the remote inbox fails asynchronously (e.g. 404 because remote user has no consent), the local request remains pending.
  → *Mitigation*: The outbound follow is visible in "Outgoing Requests" with a "Cancel" action, allowing the user to withdraw failed requests.
