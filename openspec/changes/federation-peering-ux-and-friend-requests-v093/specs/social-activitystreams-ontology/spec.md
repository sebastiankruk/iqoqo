## ADDED Requirements

### Requirement: Federated Friends Request Direction Segregation

The system SHALL separate pending federated relationships into `outgoing` when initiated by the local user and `incoming` when received from a remote actor.

#### Scenario: Outbound federated friend request appears in outgoing list

- **WHEN** a local user sends a friend request to a remote federated actor (e.g. `@user@remote.domain`) and requests `GET /api/profile/friends`
- **THEN** the pending relationship is listed in the `outgoing` array and is NOT listed in the `incoming` array

#### Scenario: Inbound federated friend request appears in incoming list

- **WHEN** a remote actor delivers an inbound ActivityPub `Follow` activity to a local user and the local user requests `GET /api/profile/friends`
- **THEN** the pending relationship is listed in the `incoming` array and is NOT listed in the `outgoing` array
