# federated-friends-and-loans Delta Specification

## ADDED Requirements

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
