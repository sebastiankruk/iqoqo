## MODIFIED Requirements

### Requirement: SQL Pagination, HTTP Content Negotiation, and Query-Parameter Negotiation on Share Endpoints

`GET /api/public/share/<token>` and canonical `GET /share/<token>` (including `?page=<n>`) SHALL support HTTP Content Negotiation for `Accept: application/ld+json` and `Accept: application/json+ld` (as well as `text/turtle`, `application/n-triples`, and `application/rdf+xml`), returning raw RDF/JSON-LD with `Content-Type: application/ld+json`. `GET /api/public/share/<token>` SHALL support SQL `page` and `per_page` pagination (`LIMIT`/`OFFSET`) returning `total`, `page`, `per_page`, `pages`, and `items` (and applying `page`/`per_page` when provided on RDF/JSON-LD requests), and `GET /api/public/share/<token>` plus `GET /api/public/rdf/share/<token>` SHALL accept `?format=jsonld|turtle|rdfxml` and `?limit=<n>` clamped to a maximum of `2000`. All share endpoints SHALL enforce the `SharedCollection`'s configured `visibility_scope` (`public_only` default restricting anonymous callers to `visibility == "public"` while granting authenticated accepted friends/owner access to `friends_only`; `friends_and_public` permitting `public` and `friends_only`; `all` permitting `public`, `friends_only`, and `private` items), and each serialized item SHALL include top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, and `country`.

#### Scenario: Canonical `/share/<token>` responds to `Accept: application/ld+json` and `application/json+ld`

- **GIVEN** a public shared collection at `/share/<token>` (or `/share/<token>?page=2`)
- **WHEN** a client requests `/share/<token>` (or `/share/<token>?page=2`) with `Accept: application/ld+json` or `application/json+ld`
- **THEN** the server MUST route to the RDF/JSON-LD serializer and return `200 OK` with `Content-Type: application/ld+json` for that collection (or page).

#### Scenario: Paginated JSON response

- **GIVEN** a public shared collection with 120 audio items
- **WHEN** a client requests `GET /api/public/share/<token>?page=2&per_page=48`
- **THEN** the response MUST return `page: 2`, `per_page: 48`, `total: 120`, `pages: 3`, and 48 items for page 2 using SQL `LIMIT`/`OFFSET`.

#### Scenario: Limit clamped on RDF export

- **WHEN** a client requests `limit=999999`
- **THEN** the response MUST contain at most 2000 items.

#### Scenario: Hidden items excluded

- **GIVEN** a shared collection with default `visibility_scope == "public_only"` containing an item with `is_hidden == True` (`visibility == "private"`)
- **WHEN** any page or format is requested
- **THEN** that `private` (`is_hidden == True`) item MUST NOT appear.

#### Scenario: Non-public items obey visibility_scope

- **GIVEN** a shared collection containing `public`, `friends_only`, and `private` (`is_hidden == True`) items
- **WHEN** `visibility_scope` is `"public_only"` (default) and the requester is an authenticated accepted friend or owner
- **THEN** `friends_only` items MUST appear alongside `public` items while `private` items remain excluded.
- **WHEN** `visibility_scope` is `"all"` and the requester presents the valid share token
- **THEN** matching `public`, `friends_only`, and `private` items owned by the creator MUST appear across JSON, RDF, and RSS responses.

#### Scenario: Unknown format rejected

- **WHEN** a client requests `?format=unknown`
- **THEN** the API MUST return a JSON error with code `400`.
