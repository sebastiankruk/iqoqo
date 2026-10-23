## ADDED Requirements

### Requirement: Federated Actor Attribute Resolution and Typed Friendship Routing
The system SHALL resolve remote `FederationActor` records using their canonical schema attributes (`actor_uri`, `username`, `display_name`) and SHALL route friend response and removal operations to either `UserFriendship` (local) or `FederationFollower` (federated) without cross-table primary-key collision.

#### Scenario: Listing local and federated friends
- **WHEN** an authenticated user calls `GET /api/v1/profile/friends` while having both local `UserFriendship` rows and federated `FederationFollower` rows
- **THEN** the system returns both local and federated entries with `username`, `display_name`, `actor_uri`, and `is_federated` populated without raising `AttributeError`

#### Scenario: Removing a federated friend vs local friend
- **WHEN** a user deletes a federated friend entry (`is_federated=true`) from their Friends list
- **THEN** the system removes the corresponding `FederationFollower` row and leaves any local `UserFriendship` with the same integer ID untouched

### Requirement: Loan Request Visibility Authorization and Shadow Borrower Integrity
The system SHALL verify that a target `Item` is visible to the requester (`public`, or `friends_only`/`shared` for an accepted friend) before creating a local or federated `LoanRequest`, SHALL create federated shadow `User` records with a non-null locked `password_hash` satisfying `check_user_auth_method`, and SHALL verify that a `LoanRequest` belongs to a federated shadow borrower before dispatching outbound ActivityPub `Accept` or `Reject` activities.

#### Scenario: Inbound federated Offer creates shadow user and loan notification
- **WHEN** a remote accepted friend sends an ActivityPub `Offer` for an available item
- **THEN** the system persists the shadow `User` without `IntegrityError`, creates the `LoanRequest`, and emits a `loan_request` notification for `item.owner_id` targeting `/item/<id>`

#### Scenario: Rejecting unauthorized loan request on private item
- **WHEN** a local user or remote actor submits a loan request for an item with `visibility="private"` (or `visibility="friends_only"` when not an accepted friend)
- **THEN** the system rejects the request with HTTP `404` or `403` (or drops the S2S `Offer`) without creating a `LoanRequest`

### Requirement: Authenticated Friend Inventory Check Scoping
The system SHALL require caller authentication (`@optional_auth`) before honoring `include_friends=True` on `POST /api/public/u/<username>/check` and SHALL only return `friends_only` holdings when the authenticated caller is authorized to view them.

#### Scenario: Unauthenticated caller passes include_friends
- **WHEN** an unauthenticated caller sends `POST /api/public/u/<username>/check` with `{"query": "Dune", "include_friends": true}`
- **THEN** the system ignores `include_friends` (or rejects unauthorized friend enumeration), returning only `<username>`'s public holdings and performing zero outbound federated HTTP requests
