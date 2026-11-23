## MODIFIED Requirements

### Requirement: Audio Pressing RDF and JSON-LD Emission

The system SHALL emit audio pressing properties for genuine audio `Manifestation` records in both RDF (`_emit_audio_rdf_triples`) and JSON-LD: `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, and `owl:sameAs` for Discogs/MusicBrainz URIs. Absent fields SHALL be omitted, not fabricated. `_emit_audio_rdf_triples` SHALL recognize all canonical music `MediaFormat` values (including `bluray_audio`, `cd_dvd_combo`, and `unknown_audio`) and SHALL NOT emit audio pressing classes or `schema:musicReleaseFormat` when the resolved carrier format maps via `FORMAT_TO_CATEGORY` to a non-music category (such as `dvd`, `bluray`, or `book`), even if `catalog_number` or drifted `content_type` metadata is present.

#### Scenario: Pressing metadata exported

- **GIVEN** a public audio manifestation with format `vinyl`, a label, a catalog number, and an EAN
- **WHEN** the shared collection graph is serialized
- **THEN** it MUST contain `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, and `schema:gtin13`.

#### Scenario: Missing field omitted

- **GIVEN** an audio manifestation without a catalog number
- **WHEN** the graph is serialized
- **THEN** no `schema:catalogNumber` triple MUST be emitted for it.

#### Scenario: Hi-res Blu-ray Audio and CD/DVD combo manifestations emit audio pressing RDF

- **GIVEN** public audio manifestations with format `bluray_audio` or `cd_dvd_combo`
- **WHEN** `_emit_audio_rdf_triples` serializes the shared collection graph
- **THEN** it MUST emit `rdf:type schema:MusicAlbum`, `rdf:type schema:MusicRelease`, and `schema:musicReleaseFormat` with the canonical format value.

#### Scenario: Movie DVD with catalog_number does not emit MusicAlbum or musicReleaseFormat triples

- **GIVEN** a movie `Manifestation` with `format = "dvd"` (even if `meta` contains `catalog_number` or `Expression.content_type` drifted)
- **WHEN** `_emit_audio_rdf_triples` and `build_collection_rdf_graph` serialize the graph
- **THEN** `schema:MusicAlbum`, `schema:MusicRelease`, and `schema:musicReleaseFormat` triples MUST NOT be emitted for that manifestation.

## ADDED Requirements

### Requirement: Type-Safe Per-Item Schema.org Typing in Share JSON-LD Views

`renderSharedCollectionJsonLdView` (`/share/<token>/jsonld/<page>` and `/share/<token>?format=jsonld`) and `resolveSchemaType` (`frontend/lib/schema-org.ts`) SHALL assign an explicit per-item `@type` resolved from carrier format and FRBR category/expression semantics, SHALL NOT apply global audio-only `@context` aliases (`byArtist`, `musicReleaseFormat`, `recordLabel`) to non-audio items (such as movie `dvd`s or `book`s), and SHALL prevent drifted `contentType="music"` metadata from typing a `dvd` or `bluray` carrier as `MusicAlbum`.

#### Scenario: Mixed or movie share JSON-LD mini-page types DVD items as Movie without musicReleaseFormat

- **GIVEN** a shared collection page containing a movie item with `format: "dvd"` (with `content_type: "movie"` or drifted `"music"`)
- **WHEN** `renderSharedCollectionJsonLdView` or `buildCollectionJsonLd` renders the JSON-LD payload
- **THEN** the DVD entry MUST carry `@type: "Movie"` and MUST NOT emit `musicReleaseFormat`, `byArtist`, or `recordLabel`.

#### Scenario: Audio item in JSON-LD mini-page retains compact audio pressing properties

- **GIVEN** a shared collection page containing a music item with `format: "vinyl"`, `publisher: "Warp Records"`, and `catalog_number: "WARPLP1"`
- **WHEN** `renderSharedCollectionJsonLdView` renders the JSON-LD payload
- **THEN** the vinyl entry MUST carry `@type: "MusicAlbum"` (or `"MusicRelease"`) along with `musicReleaseFormat: "vinyl"`, `recordLabel: "Warp Records"`, and `catalogNumber: "WARPLP1"`.
