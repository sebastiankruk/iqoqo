# federated-friends-and-loans Specification

## Purpose
Cross-instance friend following, collection/wishlist discovery, and ActivityPub loan request workflows.

## Requirements

### Requirement: Cross-Instance Loan Workflows

The system SHALL allow users to request loans from federated friends and dispatch ActivityPub Accept/Reject responses.

#### Scenario: Remote loan request approved

- **WHEN** Owner approves an incoming loan Offer from a remote friend
- **THEN** Item status changes to lent, ItemCustodyEvent is created, and as:Accept is delivered.

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

### Requirement: Automatic Sender Profile Consent and Key Provisioning on Outbound Federated Follow
When a local user initiates an outbound federated friend request (`Follow`) to a remote `@user@domain` handle, the system SHALL automatically ensure the sender has an active `FederationConsent` record with `federated_profile=True` and a provisioned RSA-2048 keypair before dispatching the signed `Follow` activity, so the receiving instance can dereference the sender's Actor IRI and verify the HTTP Signature.

#### Scenario: User with uninitialized or disabled federated_profile sends outbound federated friend request

- **WHEN** User A (whose `FederationConsent` does not exist or has `federated_profile=False`) submits an outbound friend request to `@userB@peer.example`
- **THEN** the system SHALL enable `federated_profile=True` (without implicitly enabling `federated_collection`), ensure User A's RSA-2048 keypair exists, and serve User A's Actor JSON-LD document (`200 OK`) when `peer.example` dereferences `keyId` during inbox HTTP signature verification

### Requirement: Timestamp-Aware Directional Resolution for Crossover Federated Follows
When determining whether a `pending` `FederatedFriendship` is `incoming` or `outgoing` in `list_friends` and `respond_friend_request`, the system SHALL compare the timestamp of the most recent outbound `Follow` activity (`direction="outbound"`) against the most recent inbound `Follow` activity (`direction="inbound"`) for that `remote_actor_uri`, classifying the request according to whichever direction occurred most recently.

#### Scenario: Remote user sends a new inbound Follow after a prior stale outbound Follow

- **WHEN** User B previously sent an outbound `Follow` to User A at $t_1$, and User A subsequently sends an inbound `Follow` to User B at $t_2 > t_1$ while the `FederatedFriendship` is `pending`
- **THEN** `list_friends` for User B SHALL classify the friendship as `direction="incoming"` (displaying it in the `Incoming` tab), and `respond_friend_request` (`accept` or `reject`) by User B SHALL succeed without raising `Cannot respond to an outgoing request you initiated`

#### Scenario: Requester attempts to self-accept an outgoing pending Follow

- **WHEN** User A sent the most recent `Follow` (`direction="outbound"`) to User B and no newer inbound `Follow` from User B exists
- **THEN** any attempt by User A to call `respond_friend_request` (`accept` or `reject`) on that `fed:<id>` request SHALL be rejected with HTTP 400 (`Cannot respond to an outgoing request you initiated; use cancel instead`)

### Requirement: Canonical Actor IRI in Accept Payloads and Spoofing Validation
When a local user accepts an incoming federated `Follow` request, the dispatched `Accept` activity's inner `Follow.object` field SHALL contain the local user's full canonical Actor IRI (`https://<domain>/ap/users/<username>`) rather than an internal `local:<id>` identifier, and `handle_accept` on the receiving instance SHALL validate that the `Accept` actor matches `remote_actor_uri` while accepting either the canonical Actor IRI or `local:<user_id>` in the inner `Follow.object`.

#### Scenario: Recipient accepts federated friend request and remote inbox validates Accept against spoofing

- **WHEN** User B on Instance B accepts a `pending` incoming friend request (`fed:<id>`) from User A on Instance A
- **THEN** Instance B SHALL dispatch a signed `Accept` activity whose `object.object` is User B's canonical Actor IRI, and Instance A's `handle_accept` handler SHALL verify the actor match and transition User A's `FederatedFriendship` to `accepted` without false-positive spoofing rejection

### Requirement: Disk-Authoritative Actor Public Key Synchronization
When resolving a local user's public key PEM via `get_actor_public_key(user)`, the system SHALL derive the public key directly from the private key file on disk (`data/federation_keys/user_<id>.pem`) when present and synchronize `user.federation_public_key` in the database if it differs, ensuring the public key published in `/ap/users/<username>` always matches the private key used by `sign_request`.

#### Scenario: User database public key column drifts from private key file on disk

- **WHEN** `data/federation_keys/user_<id>.pem` exists on disk and `user.federation_public_key` in the database is empty or contains an outdated PEM string
- **THEN** `get_actor_public_key(user)` SHALL return the public key derived from the disk private key and update `user.federation_public_key`, so remote inbox HTTP signature verification succeeds (`202 Accepted`)

### Requirement: Profile Consent Endpoint Synchronization with FederationConsent
When a user updates consent via `POST /api/profile/consent` with `consent_type="federation"`, the backend SHALL synchronize the boolean state with the user's `FederationConsent.federated_profile` record and provision RSA keys when enabled.

#### Scenario: User toggles federation consent via /api/profile/consent

- **WHEN** an authenticated user sends `POST /api/profile/consent` with `{"consent_type": "federation", "granted": true}`
- **THEN** both `ConsentRecord` and `FederationConsent.federated_profile=True` SHALL be persisted in the database alongside the user's RSA keypair

### Requirement: Scoped Inbound Activity Resolution for Pending Friendships
The system SHALL scope inbound `Follow` activity queries in `list_friends()` and `respond_friend_request()` strictly to the pending remote actor URIs of the requesting user and verify that the target actor URI or payload object matches the requesting user's actor IRI or UUID, preventing cross-user inbound follow theft.

#### Scenario: Inbound follow intended for another local user does not misclassify
- **WHEN** Remote Actor X follows local User B, and local User A subsequently sends an outgoing follow to Remote Actor X
- **THEN** User A's pending follow with Actor X SHALL remain classified as `outgoing` and User A SHALL NOT be able to self-accept Actor X's follow to User B

### Requirement: Outbound Reject and Undo ActivityPub Dispatch
The system SHALL dispatch an outbound ActivityPub `Reject(Follow)` activity when a user rejects an inbound federated follow request (`action == "reject"`), and SHALL dispatch an outbound `Undo(Follow)` activity when a user cancels an outgoing request or removes an accepted federated friend.

#### Scenario: User rejects inbound federated follow request
- **WHEN** an authenticated user responds with `action="reject"` to a pending inbound federated friend request
- **THEN** the system removes the local `FederationFollower` record and dispatches an outbound `Reject(Follow)` activity to the remote actor's inbox

#### Scenario: User removes an accepted federated friend
- **WHEN** an authenticated user removes an active federated friend
- **THEN** the system removes the local `FederationFollower` record and dispatches an outbound `Undo(Follow)` activity to the remote actor's inbox
