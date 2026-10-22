## Why

In release `v0.9.2` (Federated Social Library), collectors need a middle ground between strictly `PRIVATE` shelves (visible only to the owner) and globally `PUBLIC` shelves (exposed to anonymous visitors and public Semantic Web endpoints). While the in-product documentation and federated lending architecture reference a three-tier privacy model (`PRIVATE`, `FRIENDS_ONLY`, `PUBLIC`), the underlying database models and UI previously only supported binary item visibility (`is_hidden = True/False`, `default_item_visibility IN ('private', 'public')`) and lacked unified local + federated Friends management and `Friends` collection/dashboard scope filtering.

## What Changes

- **Three-Tier Visibility Cascading (`PRIVATE`, `FRIENDS_ONLY`, `PUBLIC`)**:
  - Extend `User.visibility` and `User.default_item_visibility` to support `'private'`, `'friends_only'` (with backward-compatible alias `'shared'`), and `'public'`.
  - Add `Item.visibility` (`'private' | 'friends_only' | 'public'`) with automatic synchronization to `Item.is_hidden` (`is_hidden = (visibility != 'public')`) so existing public-only SPARQL and anonymous queries remain leak-proof while accepted friends can view `friends_only` items.
  - Apply `user.default_item_visibility` automatically when scanning or creating new Items, and allow per-Item visibility overrides in the Item Edit dialog.
- **Unified Friends Model & Management UI**:
  - Support both local user-to-user friendships (`UserFriendship` with `pending` / `accepted` status) and federated ActivityPub friends (`FederationFollower` with `status == 'accepted'`).
  - Expose unified `/api/profile/friends` endpoints (list friends, send friend request by local username/email or `@user@domain` handle, accept/reject requests, remove friend) and a Friends management card on `/profile`.
- **Dashboard & Collection `Friends` Scope Toggle**:
  - Extend Dashboard (`StatsCards` / insights) and Collection (`/collection`) scope toggles to support `Personal` (`My Collection`), `Friends`, and `Global` (`Instance`), enabling collectors to browse and borrow `PUBLIC` and `FRIENDS_ONLY` items owned by their accepted friends.

## Capabilities

### New Capabilities
- `three-tier-item-and-profile-visibility`: Cascading `private`, `friends_only`, and `public` visibility across user profiles, default item settings, and individual `F4` physical items.
- `unified-friends-social-graph`: Local and federated friend request, acceptance, and authorization checks gating access to `friends_only` shelves and lending workflows.
- `friends-scope-discovery`: Dashboard statistics and Collection browsing filtered to items shared by accepted friends.

## Impact

- Database: Adds linear Alembic migration (`v0_9_2_friends_visibility`) extending visibility check constraints, adding `Item.visibility`, and creating `user_friendships` table.
- Backend API: Updates `/api/profile`, `/api/items`, `/api/collection`, and `/api/federation` to enforce 3-tier visibility and serve friend-scoped items.
- Frontend: Updates `/profile`, `EditItemDialog`, `StatsCards`, and `/collection` with `Friends Only` visibility controls, Friends management UI, and `Friends` scope filtering.
