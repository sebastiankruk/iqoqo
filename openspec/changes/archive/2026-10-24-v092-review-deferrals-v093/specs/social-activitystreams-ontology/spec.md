## ADDED Requirements

### Requirement: ActivityStreams 2.0 and Linked Data Social Graph Serialization
The RDF export (`ExportService`) and public JSON-LD endpoints MUST serialize social relationships (`foaf:knows`, `as:Follow`) and lending custody states (`frbroo:R28_curated`, `iqoqo:custodyHolder`, `schema:BorrowAction`) using standard ActivityStreams 2.0 (`https://www.w3.org/ns/activitystreams#`), FOAF (`http://xmlns.com/foaf/0.1/`), and Schema.org vocabularies.

#### Scenario: Exporting a user profile and collection as JSON-LD or Turtle
- **WHEN** a user exports their collection via `ExportService` (`export_rdf`) or a client fetches `/api/v1/public/users/<username>/profile.jsonld` with `Accept: application/ld+json` or `text/turtle`
- **THEN** the RDF graph includes `foaf:knows` triples for confirmed mutual friends (when profile/social visibility permits) and `iqoqo:custodyHolder` triples for active public loans without leaking private borrower identities
