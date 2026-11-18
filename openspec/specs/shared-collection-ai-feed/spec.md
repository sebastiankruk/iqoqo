# shared-collection-ai-feed Specification

## Purpose
TBD - created by archiving change shared-collection-semantic-audio-graph-and-ai-feed-v103. Update Purpose after archive.

## Requirements

### Requirement: Audio Pressing RDF and JSON-LD Emission

The system SHALL emit audio pressing properties for audio `Manifestation` records in both RDF (`_emit_audio_rdf_triples`) and JSON-LD: `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, and `owl:sameAs` for Discogs/MusicBrainz URIs. Absent fields SHALL be omitted, not fabricated.

#### Scenario: Pressing metadata exported

- **GIVEN** a public audio manifestation with format `vinyl`, a label, a catalog number, and an EAN
- **WHEN** the shared collection graph is serialized
- **THEN** it MUST contain `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, and `schema:gtin13`.

#### Scenario: Missing field omitted

- **GIVEN** an audio manifestation without a catalog number
- **WHEN** the graph is serialized
- **THEN** no `schema:catalogNumber` triple MUST be emitted for it.

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

### Requirement: Human Share Page UX, 10-Page Windowed Pagination, and Subtle RDF Icon Button

`/share/[token]` SHALL render a human-first collection view without raw `<details>`/`<pre>` catalog text blocks above the cover grid, SHALL align all hero action buttons (`Share`, `RSS Feed`, and the RDF/JSON-LD button) to uniform `h-9` height with the JSON-LD trigger styled as a compact icon-only RDF button linking to the full, query-free absolute URL `https://<host>/share/<token>/jsonld/1` alongside an `sr-only` 10-page windowed `<nav aria-label="AI JSON-LD pages">`, SHALL paginate the cover grid with at most 10 visible page numbers (`first`, up to `8` around current page, `last`), and SHALL NOT label audio items "Book".

#### Scenario: No raw text dump on human share page and uniform hero buttons

- **WHEN** `/share/[token]` is rendered without `?format=jsonld`
- **THEN** no `shared-catalog-index` `<details>`/`<pre>` block MUST appear above `CollectionGrid`, `<ShareButton>` and `<PublicFeedButton>` MUST share `h-9` sizing, the RDF icon button MUST link to the full absolute URL `https://<host>/share/<token>/jsonld/1`, and multi-page collections MUST include `<nav aria-label="AI JSON-LD pages">` with query-free links.

#### Scenario: 10-page pagination window bounds

- **GIVEN** a shared collection with 25 total pages and current page `12`
- **WHEN** the pagination window is computed
- **THEN** it MUST return at most 10 page numbers consisting of page `1`, 8 pages around page `12` (`8..15`), and page `25`.

#### Scenario: Audio badge

- **GIVEN** a shared vinyl item whose format is only in `manifestation_meta.format`
- **WHEN** its card renders
- **THEN** the badge MUST read the real format (for example "Vinyl"), never "Book".

### Requirement: Chromeless Query-Free Paginated HTML-Wrapped JSON-LD Mini-Page for AI Agents

When `/share/[token]/jsonld/[page]` (or `/share/[token]?format=jsonld&page=<n>`) is requested with `Accept: text/html`, Next.js SHALL render a minimal `text/html` document without `<Navbar />` or `<Footer />` containing a `<nav aria-label="JSON-LD Pages">` with full, query-free absolute links for the 10-page window (`first`, up to `8` around current page, `last`) and a `<pre id="jsonld-payload">` with minified Schema.org JSON-LD (`per_page = 60` items) including `totalItems`, `page`, `perPage`, `totalPages`, `nextPage`, `pages`, and `itemListElement`.

#### Scenario: Chromeless JSON-LD mini-page rendering

- **GIVEN** a shared collection with 365 audio items
- **WHEN** `/share/<token>/jsonld/1` (or `/share/<token>?format=jsonld&page=1`) is rendered on the server
- **THEN** the response MUST omit `<Navbar />` and `<Footer />`, MUST render `<pre id="jsonld-payload">` with minified Schema.org JSON-LD for page 1 (`totalItems: 365`, `perPage: 60`, `totalPages: 7`, full query-free `https://.../share/<token>/jsonld/<n>` URLs in `pages`), and MUST render `<nav aria-label="JSON-LD Pages">` with full query-free `<a href="https://.../share/<token>/jsonld/<n>">` links.
