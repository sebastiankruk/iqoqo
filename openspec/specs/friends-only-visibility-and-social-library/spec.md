# friends-only-visibility-and-social-library Specification

## Purpose
Three-tier cascading visibility ('private', 'friends_only', 'public'), unified local and federated friendship management, and Friends scope filtering across Collection and Dashboard.

## Requirements

### Requirement: Three-Tier Cascading Visibility (`private`, `friends_only`, `public`)

The system MUST support three visibility tiers (`private`, `friends_only`, `public`, plus legacy alias `shared`) across `User.visibility`, `User.default_item_visibility`, and individual `Item.visibility` (`F4`), including in both `PUT /api/profile/` and `PUT /api/v1/profile/visibility-defaults`, and MUST omit the dead `"Public Profile"` link from the main navigation bar while forwarding authentication cookies during server-side rendering of `/u/[username]`.

#### Scenario: User configures default item visibility to Friends Only and overrides a single item

- **GIVEN** an authenticated collector in Profile Settings (`/profile`)
- **WHEN** the collector sets `Profile Visibility` or `Default Item Visibility` to `friends_only` via `PUT /api/profile/` or `PUT /api/v1/profile/visibility-defaults` and scans or creates a new Item
- **THEN** `PUT /api/profile/` accepts `"friends_only"` with HTTP `200 OK`, persists `visibility = 'friends_only'` and `default_item_visibility = 'friends_only'`, and newly created Items inherit `visibility = 'friends_only'`
- **AND** when the collector edits an individual Item via `EditItemDialog` and sets its visibility to `private` or `public`, the item-specific visibility overrides the account default

#### Scenario: Authorization of Friends-Only items across viewers

- **GIVEN** an Item with `visibility = 'friends_only'` owned by User A (or a profile with `User.visibility = 'friends_only'`)
- **WHEN** an anonymous visitor or non-friend User C views User A's profile (`/u/<username>`), collection, or public SPARQL/RDF endpoints
- **THEN** the Item (or non-public profile) is omitted or returns 404
- **WHEN** User A or an accepted friend User B visits `/u/<username>` or views User A's collection
- **THEN** the Next.js `/u/[username]` server component forwards the caller's session cookie to `/api/public/u/<username>` so the profile and `friends_only` items render without a 404, and the top navigation bar (`navbar.tsx`) does not render a dead `"Public Profile"` menu link

### Requirement: Unified Local and Federated Friends Management

The system MUST allow users to request, accept, reject, and list friendships with both local users on the same instance and remote ActivityPub actors on federated instances, and MUST allow each user to configure their own per-user `auto_accept_follows` preference in Profile Federation Settings (`/api/v1/profile/federation-consent`).

#### Scenario: User sends and accepts a friend request

- **GIVEN** authenticated users on a local or federated iqoqo instance
- **WHEN** User A sends a friend request to local User B (or remote `@user@domain`) and User B accepts the request
- **THEN** both users appear in each other's accepted Friends list in `/profile`
- **AND** an in-app notification is delivered to the recipient upon request and acceptance

#### Scenario: User configures per-user auto-accept for follow requests from trusted peers

- **GIVEN** an authenticated collector in Profile Settings (`/profile`) with `federated_profile` enabled
- **WHEN** the collector toggles `"Auto-Accept Follow Requests from Trusted Peers"` (`auto_accept_follows`) in `FederationConsentSettings`
- **THEN** `PUT /api/v1/profile/federation-consent` persists `auto_accept_follows` on the user's `FederationConsent` record, and subsequent inbound `Follow` requests from `trusted` peer instances are automatically accepted only when this user toggle is `true`

### Requirement: Dashboard and Collection Friends Scope Filtering
The frontend and backend MUST support a `friends` scope alongside `personal` (`My Collection`) and `global` (`Instance`) in Collection browsing and Dashboard statistics.

#### Scenario: Collector switches Collection or Dashboard scope to Friends

- **GIVEN** an authenticated collector with at least one accepted friend
- **WHEN** the collector selects the `Friends` scope in `/collection` or Dashboard `StatsCards`
- **THEN** the system returns and renders items owned by accepted friends whose visibility is `public` or `friends_only`

### Requirement: Four-Tier User Visibility Database Check Constraint Parity
The PostgreSQL database schema and SQLAlchemy `User` model constraints (`check_user_visibility` and `check_user_default_item_visibility`) SHALL permit all four canonical visibility tiers (`'private'`, `'friends_only'`, `'shared'`, `'public'`) with a linear Alembic migration upgrading existing databases.

#### Scenario: User updates profile visibility and default item visibility to friends_only

- **WHEN** an authenticated user submits `PUT /api/profile` with `{"visibility": "friends_only", "default_item_visibility": "friends_only"}`
- **THEN** the database transaction SHALL succeed with HTTP 200 (never raising `CheckViolation`) and persist both fields as `"friends_only"`

### Requirement: Dynamic Friends-Only Visibility Across Full Friendship Lifecycle
Items and profiles configured with `visibility="friends_only"` SHALL dynamically reflect friendship state changes across the entire lifecycle (`none` $\to$ `pending_outgoing` / `pending_incoming` $\to$ `accepted` $\to$ `rejected` / `cancelled` / `unfollowed`) for both local (`Friendship`) and federated (`FederatedFriendship`) relationships.

#### Scenario: Friends-only item access transitions across pending, accepted, and unfollowed states

- **WHEN** User B owns an item with `visibility="friends_only"` and User A transitions through `none`, `pending`, `accepted`, and `unfollowed` (`Undo(Follow)`) states with User B
- **THEN** `is_friend_of(user_a, user_b)` and item visibility checks SHALL return `False` while `none` or `pending`, `True` while `accepted`, and immediately revert to `False` once the friendship is cancelled, rejected, or removed
