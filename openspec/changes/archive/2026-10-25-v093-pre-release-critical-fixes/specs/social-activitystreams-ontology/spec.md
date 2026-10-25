## MODIFIED Requirements

### Requirement: ActivityStreams 2.0 and Linked Data Social Graph Serialization

The RDF export (`ExportService`) and public JSON-LD endpoints MUST serialize social relationships (`foaf:knows`, `as:Follow`) and lending custody states (`frbroo:R28_curated`, `iqoqo:custodyHolder`, `schema:BorrowAction`) using standard ActivityStreams 2.0 (`https://www.w3.org/ns/activitystreams#`), FOAF (`http://xmlns.com/foaf/0.1/`), and Schema.org vocabularies, attaching `iqoqo:custodyHolder` to canonical plural `{base_url}/items/{item.id}` subject URIs only when both the item and borrower permit visibility, and excluding `private` users from `foaf:knows` triples in both `ExportService.export_rdf` and `GET /api/public/u/<username>/followers`.

#### Scenario: Exporting a user profile and collection as JSON-LD or Turtle

- **WHEN** a user exports their collection via `ExportService` (`export_rdf`) or a client fetches `/api/public/u/<username>/followers`
- **THEN** the RDF graph attaches `iqoqo:custodyHolder` to `{base_url}/items/{item.id}` only for non-hidden, non-private items with public borrowers, and omits `foaf:knows` triples for friends whose profile `visibility` is `private` (or non-`public` on the unauthenticated public followers endpoint)
