## Why

The v0.8.0 release milestone requires exposing the iqoqo digital library catalog as Linked Open Data (LOD) and semantic graphs for external consumers, AI agent interoperability, and user data sovereignty exports. Currently, `serialize_collection_to_rdf()` in `app/core/frbr_service.py` provides only minimal RDF triples, defaults to generic `schema:CreativeWork` for all items, suffers from N+1 query execution when traversing FRBR hierarchies, lacks relational enrichment (`schema:contributor`, `schema:isPartOf`, `schema:hasPart`, `schema:image`, `schema:Collection`, `schema:publisher`, `schema:inLanguage`, `schema:datePublished`, `prov:wasDerivedFrom`), lacks domain-specific mappings for Concerts (`schema:MusicEvent`) and Board Games (`schema:Game`), and loads entire collections into memory as monolithic graphs without streaming or chunking support. Enhancing RDF serialization with complete FRBR triple coverage, query optimizations, and streaming output formats is critical for scalability and semantic completeness.

## What Changes

- **Schema.org Type Mapping (`SCHEMA_TYPE_MAP`)**: Map FRBR `content_type` values to granular Schema.org types, including `text` → `schema:Book`, `audiobook` → `schema:Audiobook`, `music` → `schema:MusicAlbum`, `movie` → `schema:Movie`, `board_game` → `schema:Game`, `puzzle` → `schema:Product`, and concert manifestations/events → `schema:MusicEvent`.
- **Relational & Provenance Enrichment (`_enrich_graph_from_db`)**: Enrich serialized graphs with relational semantics: `schema:contributor`, `schema:isPartOf` and `schema:hasPart` (for collections, box sets, and multi-volume works), `schema:image` (cover image URLs), `schema:Collection` root nodes, `schema:publisher`, `schema:inLanguage`, `schema:datePublished`, and `prov:wasDerivedFrom` linking external data provenance (e.g., Open Library, Allegro, MusicBrainz, BGG).
- **Fix N+1 Queries (MOD-FRBR-02)**: Eliminate lazy-loading round trips in `serialize_collection_to_rdf()` by ensuring eager loading via `joinedload()` / `selectinload()` across `Item -> Manifestation -> Expression -> Work` relationships.
- **Domain Mappings for Concerts & Board Games**: Add specialized property mappings for board games (`schema:numberOfPlayers`, `schema:Game`) and concert events (`schema:MusicEvent`, `schema:performer`, `schema:startDate`, `schema:location`).
- **Streaming RDF Serialization (`stream_collection_to_rdf`)**: Implement generator-based streaming RDF serialization for large collections that yields serialized RDF chunks (Turtle, JSON-LD lines, and N-Triples) without materializing entire collections in memory.
- **Expanded Format Support**: Add explicit format support for N-Triples (`nt`), Turtle (`turtle`), and JSON-LD (`json-ld`) across public collection endpoints and serialization services.

## Capabilities

### New Capabilities
- `semantic/rdf-serialization`: Granular Schema.org type mapping for FRBR entities, relational and provenance enrichment, eager loading query optimization (MOD-FRBR-02), domain-specific concert and board game semantics, expanded format support (Turtle, JSON-LD, N-Triples), and generator-based streaming serialization for large collections.

### Modified Capabilities

## Impact

- **Core Service**: `app/core/frbr_service.py` enhanced with `SCHEMA_TYPE_MAP`, `_enrich_graph_from_db()`, eager-loaded query paths, domain-specific mapping functions, and `stream_collection_to_rdf()`.
- **Public API**: `app/api/public.py` updated to support `text/plain` or `application/n-triples` format negotiation and streaming responses for collection export endpoints.
- **Database Performance**: Prevents database connection exhaustion and N+1 query overhead when serializing large collections (MOD-FRBR-02).
- **Dependencies**: Leverages existing `rdflib` already installed in the virtual environment.
- **Breaking Changes**: None. Existing signatures and default parameters remain backward-compatible while introducing streaming and enriched fields.
