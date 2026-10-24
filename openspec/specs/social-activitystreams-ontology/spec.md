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

### Requirement: ActivityStreams 2.0 and Linked Data Social Graph Serialization
The RDF export (`ExportService`) and public JSON-LD endpoints MUST serialize social relationships (`foaf:knows`, `as:Follow`) and lending custody states (`frbroo:R28_curated`, `iqoqo:custodyHolder`, `schema:BorrowAction`) using standard ActivityStreams 2.0 (`https://www.w3.org/ns/activitystreams#`), FOAF (`http://xmlns.com/foaf/0.1/`), and Schema.org vocabularies.

#### Scenario: Exporting a user profile and collection as JSON-LD or Turtle

- **WHEN** a user exports their collection via `ExportService` (`export_rdf`) or a client fetches `/api/v1/public/users/<username>/profile.jsonld` with `Accept: application/ld+json` or `text/turtle`
- **THEN** the RDF graph includes `foaf:knows` triples for confirmed mutual friends (when profile/social visibility permits) and `iqoqo:custodyHolder` triples for active public loans without leaking private borrower identities
