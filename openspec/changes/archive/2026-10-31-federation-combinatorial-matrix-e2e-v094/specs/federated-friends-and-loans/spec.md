## ADDED Requirements

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
