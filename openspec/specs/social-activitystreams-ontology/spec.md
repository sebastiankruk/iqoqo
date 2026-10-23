# social-activitystreams-ontology Specification

## Purpose
OWL and SHACL ontology extensions mapping collections, friends, wishlists, and custody loans to ActivityStreams 2.0 and CIDOC CRM.

## Requirements

### Requirement: Social Semantic Web Mapping

The system SHALL serialize social interactions using standard ActivityStreams 2.0 and CIDOC CRM ontologies.

#### Scenario: Custody loan serialized as CIDOC E10

- **WHEN** An Item custody event is exported to RDF
- **THEN** Emits crm:E10_Transfer_of_Custody and validates against iqoqo-shapes.ttl.

### Requirement: FOAF Local Friend Serialization on Public Followers Endpoint
The system SHALL query accepted local `UserFriendship` peers and pass them into `serialize_user_followers_to_rdf` on `GET /api/public/u/<username>/followers` so `foaf:knows` and `iqoqo:knowsFriend` triples are emitted alongside ActivityStreams `Follow` triples.

#### Scenario: Fetching followers RDF for user with accepted local friends

- **WHEN** a client requests `GET /api/public/u/<username>/followers` for a public user who has accepted local friends
- **THEN** the returned RDF graph contains `foaf:knows` and `iqoqo:knowsFriend` triples pointing to each accepted friend's canonical `/u/<friend>` URI
