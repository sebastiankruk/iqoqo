## Context

Release `v0.9.2` introduces the Federated Social Library (ActivityPub actor discovery, cross-instance lending, notifications, and in-app documentation). However, two foundational social primitives were omitted from the initial `0.9.2` specs:
1. **Three-tier visibility (`PRIVATE`, `FRIENDS_ONLY`, `PUBLIC`)**: Previously, `User.default_item_visibility` only permitted `'private'` or `'public'`, and `Item` only stored `is_hidden: bool`. Collectors could not mark their default shelf—or specific physical copies—as visible exclusively to friends.
2. **Unified Local & Federated Friends + `Friends` Scope**: While `FederationFollower` tracked remote ActivityPub followers, local users on the same instance had no way to establish mutual friendships, and the UI lacked a `Friends` scope toggle on the Dashboard and Collection views.

## Goals / Non-Goals

**Goals:**
- Implement a three-tier visibility model (`private`, `friends_only`, `public`) at the profile, default item, and per-item levels.
- Preserve 100% backward compatibility with `Item.is_hidden` and existing SPARQL / public RDF gates (`friends_only` items MUST keep `is_hidden = True` so anonymous public endpoints and public SPARQL never leak them).
- Provide a unified friendship authorization helper `is_friend_of(viewer_user_id, owner_user_id, remote_actor_id=None)` covering both local accepted friendships (`UserFriendship`) and federated accepted followers (`FederationFollower`).
- Add `Friends` scope filtering to the Collection browser and Dashboard insights.

**Non-Goals:**
- Exposing `friends_only` items to unauthenticated public SPARQL queries (public SPARQL remains strictly `PUBLIC`-only).
- Building a public social feed or timeline wall unrelated to FRBR cataloging and lending.

## Decisions

### 1. Synchronizing `Item.visibility` with `Item.is_hidden`
- **Decision:** Add `visibility = db.Column(db.String(20), nullable=False, default="public", server_default="public")` to `Item` with `CheckConstraint("visibility IN ('private', 'friends_only', 'public')")`. Keep `is_hidden` synchronized via model property/hooks such that `is_hidden == (visibility != "public")`.
- **Rationale:** Every existing public endpoint, public RDF serializer, and public SPARQL query already filters on `Item.is_hidden.is_(False)`. By keeping `is_hidden = True` whenever `visibility in ('private', 'friends_only')`, we guarantee zero accidental data leaks in public endpoints while allowing friend-aware endpoints (`/api/items`, `/api/profile/u/<username>`, `/api/federation/friends/<id>/collections`) to authorize `visibility == 'friends_only'` when `is_friend_of(...)` is true.

### 2. Unified Local + Federated Friends Graph
- **Decision:** Introduce `UserFriendship` (`requester_id`, `addressee_id`, `status IN ('pending', 'accepted', 'rejected')`) in the `auth` schema alongside existing `FederationFollower` in the `federation` schema, and expose a unified `/api/profile/friends` REST interface.
- **Rationale:** Households, book clubs, and multi-user instances often share a single iqoqo server, while also connecting to remote instances via ActivityPub. Combining local `UserFriendship` and remote `FederationFollower` behind a unified API and UI card on `/profile` provides a seamless experience regardless of whether a friend is local (`@marek`) or remote (`@anna@books.gdansk.pl`).

### 3. Single Linear Alembic Migration (`v0_9_2_friends_visibility`)
- **Decision:** Chain `v0_9_2_friends_visibility` directly after `v0_9_2_notifications` (`len(revision) <= 32`) maintaining a single Alembic head.
- **Rationale:** Complies strictly with the project's Linear Migration DAG rule.
