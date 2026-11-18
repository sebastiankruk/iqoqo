## MODIFIED Requirements

### Requirement: SQL Pagination, HTTP Content Negotiation, and Query-Parameter Negotiation on Share Endpoints

`GET /api/public/share/<token>` and canonical `GET /share/<token>` (including `?page=<n>`) SHALL support HTTP Content Negotiation for `Accept: application/ld+json` and `Accept: application/json+ld` (as well as `text/turtle`, `application/n-triples`, and `application/rdf+xml`), returning raw RDF/JSON-LD with `Content-Type: application/ld+json`. `GET /api/public/share/<token>` SHALL support SQL `page` and `per_page` pagination (`LIMIT`/`OFFSET`) returning `total`, `page`, `per_page`, `pages`, and `items` (preserving pagination offsets on PostgreSQL full-text search filters and slicing shared `UserWorkIntent` wishlist entries including `"want_to_build"`), and `GET /api/public/share/<token>` plus `GET /api/public/rdf/share/<token>` SHALL accept `?format=jsonld|turtle|rdfxml` and `?limit=<n>` clamped to a maximum of `2000`. All share endpoints SHALL only emit items with `is_hidden == False` in collections with `visibility == "public"`, and each serialized item SHALL include top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, and `country`.

#### Scenario: Canonical `/share/<token>` responds to `Accept: application/ld+json` and `application/json+ld`

- **GIVEN** a public shared collection at `/share/<token>` (or `/share/<token>?page=2`)
- **WHEN** a client requests `/share/<token>` (or `/share/<token>?page=2`) with `Accept: application/ld+json` or `Accept: application/json+ld`
- **THEN** the server MUST route to the RDF/JSON-LD serializer and return `200 OK` with `Content-Type: application/ld+json` for that collection (or page).

#### Scenario: Paginated JSON response

- **GIVEN** a public shared collection with 120 audio items
- **WHEN** a client requests `GET /api/public/share/<token>?page=2&per_page=48`
- **THEN** the response MUST return `page: 2`, `per_page: 48`, `total: 120`, `pages: 3`, and 48 items for page 2 using SQL `LIMIT`/`OFFSET`.

#### Scenario: Limit clamped on RDF export

- **WHEN** a client requests `limit=999999`
- **THEN** the response MUST contain at most 2000 items.

#### Scenario: Hidden items excluded

- **GIVEN** a shared collection containing an item with `is_hidden == True`
- **WHEN** any page or format is requested
- **THEN** that item MUST NOT appear.

#### Scenario: Unknown format rejected

- **WHEN** a client requests `?format=unknown`
- **THEN** the API MUST return a JSON error with code `400`.
