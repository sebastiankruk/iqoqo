## ADDED Requirements

### Requirement: Audio Pressing RDF and JSON-LD Emission

The system SHALL emit audio pressing properties for audio `Manifestation` records in both RDF (`_emit_audio_rdf_triples`) and SSR JSON-LD: `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, and `owl:sameAs` for Discogs/MusicBrainz URIs. Absent fields SHALL be omitted, not fabricated.

#### Scenario: Pressing metadata exported

- **GIVEN** a public audio manifestation with format `vinyl`, a label, a catalog number, and an EAN
- **WHEN** the shared collection graph is serialized
- **THEN** it MUST contain `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, and `schema:gtin13`.

#### Scenario: Missing field omitted

- **GIVEN** an audio manifestation without a catalog number
- **WHEN** the graph is serialized
- **THEN** no `schema:catalogNumber` triple MUST be emitted for it.

### Requirement: Query-Parameter Content Negotiation on Share Endpoints

`GET /api/public/share/<token>` and `GET /api/public/rdf/share/<token>` SHALL accept `?format=jsonld|turtle|rdfxml` and `?limit=<n>` clamped to a maximum of `2000`, and SHALL only emit items with `is_hidden == False` in collections with `visibility == "public"`. Each serialized item SHALL include top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, and `country`.

#### Scenario: Full collection by URL alone

- **GIVEN** a public shared collection with 365 audio items
- **WHEN** a client requests `?format=jsonld&limit=1000`
- **THEN** the response MUST contain all 365 items.

#### Scenario: Limit clamped

- **WHEN** a client requests `limit=999999`
- **THEN** the response MUST contain at most 2000 items.

#### Scenario: Hidden items excluded

- **GIVEN** a shared collection containing an item with `is_hidden == True`
- **WHEN** any format is requested
- **THEN** that item MUST NOT appear.

#### Scenario: Unknown format rejected

- **WHEN** a client requests `?format=unknown`
- **THEN** the API MUST return a JSON error with code `400`.

### Requirement: Share Page SSR JSON-LD, Feed Link, and Correct Badges

`/share/[token]` SHALL server-render JSON-LD covering the shared collection (up to 1,000 items), SHALL expose a "JSON-LD / AI Feed" link next to the RSS link plus `<link rel="alternate" type="application/ld+json">` in the head, and SHALL NOT label audio items "Book".

#### Scenario: JSON-LD in server HTML

- **WHEN** `/share/[token]` is rendered on the server
- **THEN** the HTML MUST include an `application/ld+json` script containing `MusicAlbum` nodes with `musicReleaseFormat`, `gtin13`, `catalogNumber`, and `recordLabel`.

#### Scenario: Audio badge

- **GIVEN** a shared vinyl item whose format is only in `manifestation_meta.format`
- **WHEN** its card renders
- **THEN** the badge MUST read the real format (for example "Vinyl"), never "Book".
