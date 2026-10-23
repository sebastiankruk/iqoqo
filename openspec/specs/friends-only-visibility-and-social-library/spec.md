# friends-only-visibility-and-social-library Specification

## Purpose
Three-tier cascading visibility ('private', 'friends_only', 'public'), unified local and federated friendship management, and Friends scope filtering across Collection and Dashboard.

## Requirements

### Requirement: Three-Tier Cascading Visibility (`private`, `friends_only`, `public`)
The system MUST support three visibility tiers (`private`, `friends_only`, `public`) across `User.visibility`, `User.default_item_visibility`, and individual `Item.visibility` (`F4`).

#### Scenario: User configures default item visibility to Friends Only and overrides a single item

- **GIVEN** an authenticated collector in Profile Settings (`/profile`)
- **WHEN** the collector sets `Default Item Visibility` to `friends_only` and scans or creates a new Item
- **THEN** the newly created `Item` inherits `visibility = 'friends_only'` (and `is_hidden = True` for anonymous public queries)
- **AND** when the collector edits an individual Item via `EditItemDialog` and sets its visibility to `private` or `public`, the item-specific visibility overrides the account default

#### Scenario: Authorization of Friends-Only items across viewers

- **GIVEN** an Item with `visibility = 'friends_only'` owned by User A
- **WHEN** an anonymous visitor or non-friend User C views User A's profile, collection, or public SPARQL/RDF endpoints
- **THEN** the Item is completely omitted from results and counts
- **WHEN** an accepted friend User B (or remote accepted friend Actor B with User A's federation consent) views User A's collection or filters by `Friends` scope
- **THEN** the Item is visible and eligible for borrowing

### Requirement: Unified Local and Federated Friends Management
The system MUST allow users to request, accept, reject, and list friendships with both local users on the same instance and remote ActivityPub actors on federated instances.

#### Scenario: User sends and accepts a friend request

- **GIVEN** authenticated users on a local or federated iqoqo instance
- **WHEN** User A sends a friend request to local User B (or remote `@user@domain`) and User B accepts the request
- **THEN** both users appear in each other's accepted Friends list in `/profile`
- **AND** an in-app notification is delivered to the recipient upon request and acceptance

### Requirement: Dashboard and Collection Friends Scope Filtering
The frontend and backend MUST support a `friends` scope alongside `personal` (`My Collection`) and `global` (`Instance`) in Collection browsing and Dashboard statistics.

#### Scenario: Collector switches Collection or Dashboard scope to Friends

- **GIVEN** an authenticated collector with at least one accepted friend
- **WHEN** the collector selects the `Friends` scope in `/collection` or Dashboard `StatsCards`
- **THEN** the system returns and renders items owned by accepted friends whose visibility is `public` or `friends_only`
