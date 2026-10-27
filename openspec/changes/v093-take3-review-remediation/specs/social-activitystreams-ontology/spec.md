## MODIFIED Requirements

### Requirement: ActivityStreams 2.0 and Linked Data Social Graph Serialization

The RDF export (`ExportService`) and public JSON-LD endpoints MUST serialize social relationships (`foaf:knows`, `as:Follow`) and lending custody states (`frbroo:R28_curated`, `iqoqo:custodyHolder`, `schema:BorrowAction`) using standard ActivityStreams 2.0 (`https://www.w3.org/ns/activitystreams#`), FOAF (`http://xmlns.com/foaf/0.1/`), and Schema.org vocabularies, eager-loading `Item.borrower` and iterating items in bounded SQL chunks during `ExportService.export_rdf`, attaching `iqoqo:custodyHolder` to canonical plural `{base_url}/items/{item.id}` subject URIs only when both the item and borrower permit visibility, enforcing explicit `Item.visibility == "public"` alongside `Item.is_hidden == False` on unauthenticated batch/instance RDF endpoints, excluding `private` users from `foaf:knows` triples, and applying `Referrer-Policy: no-referrer` on `/share/:path*` routes.

#### Scenario: Exporting a user profile and collection as JSON-LD or Turtle

- **WHEN** a user with loaned items exports their collection via `ExportService.export_rdf` or a client fetches `/api/public/u/<username>/followers`
- **THEN** the export processes items in bounded SQL batches with `borrower` eager-loaded (zero per-item borrower N+1 queries), attaches `iqoqo:custodyHolder` to `{base_url}/items/{item.id}` only for visible items with public borrowers, and omits `foaf:knows` triples for `private` profiles

#### Scenario: Public share route suppresses Referer leakage

- **WHEN** a visitor loads a shared collection page at `/share/<token>`
- **THEN** the frontend response includes `Referrer-Policy: no-referrer` so external subresources or links do not receive the share URL token
