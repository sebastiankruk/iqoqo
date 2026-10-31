## ADDED Requirements

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
