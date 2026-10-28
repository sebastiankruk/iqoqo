## ADDED Requirements

### Requirement: ActivityPub Follow Direction and Outbound Self-Response Prevention

The ActivityPub friendship and follow lifecycle SHALL distinguish between outbound and inbound pending Follow requests, and the system SHALL prohibit users from accepting or rejecting outbound follow requests they initiated themselves.

#### Scenario: User cannot respond to an outbound follow request they initiated

- **WHEN** an authenticated user attempts to call `POST /api/profile/friends/<friendship_id>/respond` with action `accept` or `reject` on a federated relationship where the local user is the initiator of the outbound `Follow` activity
- **THEN** the API rejects the request with HTTP `400 Bad Request` and an error indicating that outgoing requests cannot be accepted or rejected and must be cancelled instead

#### Scenario: User can cancel an outbound federated follow request

- **WHEN** an authenticated user calls `DELETE /api/profile/friends/<friendship_id>` for an outbound pending federated follow request
- **THEN** the system removes the pending follow relationship and returns HTTP `200 OK`
