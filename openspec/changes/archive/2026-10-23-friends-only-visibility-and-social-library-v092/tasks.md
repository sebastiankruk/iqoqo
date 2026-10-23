## 1. Database & Three-Tier Visibility Model

- [x] 1.1 Create linear Alembic migration (`v0_9_2_friends_visibility` chained from `v0_9_2_notifications`) updating `User` visibility constraints, adding `Item.visibility` (`private`, `friends_only`, `public`), and creating the `user_friendships` table
- [x] 1.2 Update `User` (`app/db/auth.py`) and `Item` (`app/db/core.py`) models to support `'private'`, `'friends_only'`, and `'public'` visibility while keeping `Item.is_hidden` synchronized (`is_hidden = (visibility != 'public')`)
- [x] 1.3 Apply `user.default_item_visibility` automatically during item creation/scanning and expose per-item `visibility` updates in `PATCH /api/items/<id>` and bulk item operations

## 2. Unified Friends Backend API & Access Control

- [x] 2.1 Implement `UserFriendship` model and `is_friend_of(viewer_user_id, owner_user_id, remote_actor_id=None)` authorization helper unifying local friendships and accepted `FederationFollower` records
- [x] 2.2 Implement `/api/profile/friends` endpoints (GET list of accepted/pending local + federated friends, POST send friend request by username/email or `@user@domain` handle, POST accept/reject, DELETE remove friend) with in-app notifications
- [x] 2.3 Update collection, item detail, public profile (`/api/profile/u/<username>`), and federated friend collection endpoints to authorize `friends_only` items for accepted friends and support `scope=friends` filtering

## 3. Frontend UI Surfaces (Profile, Item Editor, Friends Scope)

- [x] 3.1 Update `/profile` (`frontend/app/profile/page.tsx`) to offer 3-tier radio options (`Private`, `Friends Only`, `Public`) for Profile Visibility and Default Item Visibility, and add the Friends Management card
- [x] 3.2 Update `EditItemDialog` (`frontend/components/item/edit-item-dialog.tsx`) to include a 3-tier Item Visibility selector (`Private`, `Friends Only`, `Public`)
- [x] 3.3 Add `Friends` scope toggle (`My Collection` / `Friends` / `Instance`) to Dashboard `StatsCards` and `/collection` view with EN + PL translations (`frontend/messages/{en,pl}.json`)

## 4. Verification & Test Suites

- [x] 4.1 Add backend pytest suite (`tests/test_friends_visibility.py`) verifying 3-tier visibility cascading, friend request/accept flows, `scope=friends` queries, and zero leakage to anonymous/SPARQL endpoints
- [x] 4.2 Add frontend Vitest tests for 3-tier visibility controls, Friends management UI, and `Friends` scope toggle
