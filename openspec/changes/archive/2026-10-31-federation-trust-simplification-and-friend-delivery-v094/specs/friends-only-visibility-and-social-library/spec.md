## MODIFIED Requirements

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
