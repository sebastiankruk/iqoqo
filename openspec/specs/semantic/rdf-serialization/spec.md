# semantic/rdf-serialization Specification

## Purpose

Provides semantic RDF graph serialization of FRBR catalog collections with Schema.org type mapping, relational enrichment, domain mappings, and streaming chunked generation.

## Requirements

### Requirement: Granular Schema.org Type Mapping

The system SHALL map FRBR `content_type` attributes to specific Schema.org creative work and product classes instead of solely generic `schema:CreativeWork`. Supported mappings SHALL include `text` to `schema:Book`, `audiobook` to `schema:Audiobook`, `music` to `schema:MusicAlbum`, `movie` to `schema:Movie`, `board_game` to `schema:Game`, and `puzzle` to `schema:Product`.

#### Scenario: Serializing a book manifestation

- **WHEN** a manifestation with content type `text` is serialized to RDF
- **THEN** the RDF graph contains a triple asserting the manifestation URI is of type `schema:Book` as well as `frbr:Manifestation`.

#### Scenario: Serializing an album or game manifestation

- **WHEN** manifestations with content type `music` or `board_game` are serialized to RDF
- **THEN** the RDF graph asserts types `schema:MusicAlbum` and `schema:Game` respectively.

### Requirement: Relational and Metadata Property Enrichment

The system SHALL enrich RDF serializations with descriptive, relational, and structural triples extracted from entity attributes and metadata JSON payloads. These SHALL include `schema:publisher`, `schema:inLanguage`, `schema:datePublished`, `schema:contributor`, `schema:image`, and provenance triple `prov:wasDerivedFrom`.

#### Scenario: Serializing manifestation with publisher, language, and date

- **WHEN** an item's manifestation contains publisher, language, and publication year metadata
- **THEN** the output graph contains `schema:publisher`, `schema:inLanguage`, and `schema:datePublished` properties referencing the respective literals.

#### Scenario: Serializing contributors and cover images

- **WHEN** an entity has recorded contributor roles and a cover image URL
- **THEN** the output graph includes `schema:contributor` for each contributor and `schema:image` linking to the cover resource.

#### Scenario: Serializing external provenance link

- **WHEN** an entity has an external provenance origin (such as OpenLibrary, MusicBrainz, BoardGameGeek, or Allegro)
- **THEN** the RDF graph asserts a `prov:wasDerivedFrom` relation connecting the entity to its external source IRI.

### Requirement: Part-Whole and Collection Structural Representation

The system SHALL represent collection aggregations and hierarchical part-whole relations using `schema:Collection`, `schema:isPartOf`, and `schema:hasPart`.

#### Scenario: Serializing collection root node

- **WHEN** a user collection or shared collection is exported as an RDF graph
- **THEN** the graph defines a `schema:Collection` root resource with `schema:hasPart` referencing each constituent manifestation or item.

#### Scenario: Serializing multi-volume or boxed set items

- **WHEN** items or works declare parent-child or container relationships
- **THEN** the graph connects child entities to their container using `schema:isPartOf` and reciprocal `schema:hasPart`.

### Requirement: Domain Mappings for Concerts and Board Games

The system SHALL provide specialized RDF mappings for Concert events and Board Game manifestations. Concert manifestations or associated performance records SHALL map to `schema:MusicEvent` with performer, start date, and venue/location triples. Board games SHALL map to `schema:Game` with player count constraints (`schema:numberOfPlayers`).

#### Scenario: Serializing a concert event

- **WHEN** a manifestation or expression represents a concert event
- **THEN** the RDF graph declares type `schema:MusicEvent` with `schema:performer`, `schema:startDate`, and `schema:location` predicates when present.

#### Scenario: Serializing board game player constraints

- **WHEN** a board game manifestation contains min/max player counts in metadata
- **THEN** the RDF graph asserts `schema:numberOfPlayers` with the formatted player range.

### Requirement: Multi-Format Serialization Support

The system SHALL support RDF serialization in Turtle (`turtle`), JSON-LD (`json-ld`), and N-Triples (`nt`) formats, selectable via the `output_format` parameter and HTTP Content Negotiation (`Accept` header).

#### Scenario: Requesting N-Triples export

- **WHEN** a client requests a collection export with format `nt` or `Accept: application/n-triples`
- **THEN** the system returns a valid line-oriented N-Triples payload conforming to W3C N-Triples specification.

#### Scenario: Requesting Turtle export

- **WHEN** a client requests a collection export with format `turtle` or `Accept: text/turtle`
- **THEN** the system returns a valid Turtle serialization with bound namespace prefixes (`frbr`, `schema`, `sioc`, `prov`).

#### Scenario: Requesting JSON-LD export

- **WHEN** a client requests a collection export with format `json-ld` or `Accept: application/ld+json`
- **THEN** the system returns a valid JSON-LD document with a compact `@context` definition.

### Requirement: Streaming RDF Serialization for Large Collections

The system SHALL provide a generator-based streaming RDF serialization interface that yields serialized RDF chunks without requiring the entire graph of a large collection to reside concurrently in memory.

#### Scenario: Streaming collection export

- **WHEN** streaming serialization is invoked for a collection containing numerous items
- **THEN** the serialization function yields chunks of serialized triples iteratively, enabling HTTP chunked transfer responses without high memory spikes.

### Requirement: Elimination of N+1 Queries (MOD-FRBR-02)

The system SHALL ensure that queries fetching collection items for RDF serialization utilize eager loading across `Item -> Manifestation -> Expression -> Work` relationships, preventing lazy-loading round trips during graph construction.

#### Scenario: Serializing a multi-item collection without lazy queries

- **WHEN** `serialize_collection_to_rdf()` processes a list of ORM items
- **THEN** all related manifestations, expressions, and works are loaded in the initial database queries via joined/selected relationships, executing zero additional queries during graph iteration.
