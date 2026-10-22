## ADDED Requirements

### Requirement: FOAF Local Friend Serialization on Public Followers Endpoint
The system SHALL query accepted local `UserFriendship` peers and pass them into `serialize_user_followers_to_rdf` on `GET /api/public/u/<username>/followers` so `foaf:knows` and `iqoqo:knowsFriend` triples are emitted alongside ActivityStreams `Follow` triples.

#### Scenario: Fetching followers RDF for user with accepted local friends
- **WHEN** a client requests `GET /api/public/u/<username>/followers` for a public user who has accepted local friends
- **THEN** the returned RDF graph contains `foaf:knows` and `iqoqo:knowsFriend` triples pointing to each accepted friend's canonical `/u/<friend>` URI
