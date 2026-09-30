## Context

See `proposal.md` for motivation and background.

iqoqo's catalog architecture is grounded in the FRBR ontology (Work → Expression → Manifestation → Item). Semantic Linked Data export is currently handled by `serialize_collection_to_rdf()` in `app/core/frbr_service.py`, consumed by public collection endpoints in `app/api/public.py`. While the basic FRBR structural links (`frbr:embodimentOf`, `frbr:expressionOf`, `frbr:exemplarOf`) are present, the current serialization implementation exhibits several limitations:
1. Every entity is assigned generic `schema:CreativeWork`, ignoring specific types such as `Book`, `Audiobook`, `MusicAlbum`, `Movie`, `Game`, `Product`, or `MusicEvent`.
2. Relational and provenance triples are missing, including `schema:publisher`, `schema:inLanguage`, `schema:datePublished`, `schema:contributor`, `schema:isPartOf`, `schema:hasPart`, `schema:image`, and `prov:wasDerivedFrom`.
3. Collections lack a top-level `schema:Collection` root node connecting members.
4. Traversal of ORM relationships (`item.manifestation.expression.work`) during serialization causes N+1 query execution if relationships were not eagerly loaded (MOD-FRBR-02).
5. Output format is limited to monolithic Turtle and JSON-LD strings, lacking N-Triples support and stream/yield-based generation for large collections.

## Goals / Non-Goals

**Goals:**
- Introduce `SCHEMA_TYPE_MAP` in `app/core/frbr_service.py` mapping FRBR `content_type` values to specific Schema.org classes (`schema:Book`, `schema:Audiobook`, `schema:MusicAlbum`, `schema:Movie`, `schema:Game`, `schema:Product`).
- Implement `_enrich_graph_from_db()` to add `schema:publisher`, `schema:inLanguage`, `schema:datePublished`, `schema:contributor`, `schema:image`, `schema:isPartOf`, `schema:hasPart`, `schema:Collection`, and `prov:wasDerivedFrom`.
- Add specialized domain mappings for Concerts (`schema:MusicEvent`) and Board Games (`schema:Game` with player counts).
- Fix N+1 query bottlenecks in `serialize_collection_to_rdf()` and public queries using `joinedload()` / `selectinload()` eager loading (MOD-FRBR-02).
- Implement `stream_collection_to_rdf()` supporting chunked/yield-based streaming serialization for large collections.
- Expand serialization formats to support Turtle (`turtle`), JSON-LD (`json-ld`), and N-Triples (`nt`), integrated with HTTP content negotiation.

**Non-Goals:**
- Altering relational database schema or generating Alembic migrations.
- Implementing the SPARQL query engine (`/api/sparql`) or admin SPARQL explorer UI (addressed in C2).
- Implementing ActivityPub federation protocols (deferred to v0.9.0).

## Decisions

### 1. Granular Schema.org Mapping via `SCHEMA_TYPE_MAP`
- **Decision**: Define a dictionary `SCHEMA_TYPE_MAP` mapping `content_type` strings to `rdflib.URIRef(SCHEMA.<Type>)`:
  - `text` → `SCHEMA.Book`
  - `audiobook` → `SCHEMA.Audiobook`
  - `music` → `SCHEMA.MusicAlbum`
  - `movie` → `SCHEMA.Movie`
  - `board_game` → `SCHEMA.Game`
  - `puzzle` → `SCHEMA.Product`
  - Default fallback: `SCHEMA.CreativeWork`.
- **Rationale**: External LOD consumers, search engines, and AI agents require specific Schema.org types to index books, music albums, and games accurately.
- **FRBR Compliance**: The Schema.org type is asserted on the `Manifestation` URI in conjunction with `frbr:Manifestation`, preserving the strict FRBR hierarchy.

### 2. Relational & Provenance Enrichment Pipeline (`_enrich_graph_from_db`)
- **Decision**: Centralize triple enrichment into `_enrich_graph_from_db(g, item, base_url, collection_uri=None)`:
  - Extracted properties:
    - `schema:publisher`: Manifestation publisher name literal.
    - `schema:inLanguage`: Expression language literal.
    - `schema:datePublished`: Publication year or release date literal.
    - `schema:contributor`: Contributor names (illustrators, editors, translators) from metadata.
    - `schema:image`: URIRef pointing to cover image resource.
    - `prov:wasDerivedFrom`: External source URIs (Open Library, Allegro, MusicBrainz, BGG).
    - `schema:isPartOf` / `schema:hasPart`: Container work relationships and collection membership.
    - `schema:Collection`: If a collection root URI is provided, assert `collection_uri a schema:Collection` and link each manifestation via `schema:hasPart`.
- **Rationale**: Isolates metadata extraction and triple construction from serialization formatting, enabling reuse between monolithic and streaming serializers.

### 3. Specialized Domain Mappings (Concerts & Board Games)
- **Decision**:
  - Concerts: When `content_type == "concert"` or manifestation format denotes a live performance, assert `RDF.type -> SCHEMA.MusicEvent`, mapping performers to `schema:performer`, date to `schema:startDate`, and venue to `schema:location`.
  - Board Games: When `content_type == "board_game"`, assert `RDF.type -> SCHEMA.Game`, extracting `min_players` and `max_players` from metadata and adding `schema:numberOfPlayers` literal.
- **Rationale**: Concerts and board games possess domain-specific properties that cannot be represented by standard book or creative work vocabularies.

### 4. Eager Loading Query Optimization (MOD-FRBR-02)
- **Decision**: Ensure that all collection fetch queries (`fetch_user_public_collection`, `fetch_shared_collection_by_token`, and batch loaders) explicitly specify eager joins:
  `options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))`.
  Additionally, in `serialize_collection_to_rdf()`, if passed un-hydrated Item objects or IDs, check for unloaded relations or re-query with eager options before graph iteration.
- **Rationale**: Resolves MOD-FRBR-02 where serializing collections with dozens or hundreds of items triggered hundreds of individual SQL queries, causing latency and connection pool exhaustion.

### 5. Chunked Streaming Serialization (`stream_collection_to_rdf`)
- **Decision**: Implement a Python generator `stream_collection_to_rdf(items_iterable, base_url, output_format="turtle", chunk_size=50)`:
  - For `nt` (N-Triples): Line-oriented format. Each chunk constructs a small `Graph()`, enriches it, serializes to N-Triples lines, and yields the chunk. Zero global state required.
  - For `turtle`: Yields shared prefix header once, then serializes chunk subgraphs without repeating prefix definitions.
  - For `json-ld`: Serializes chunk subgraphs as JSON-LD fragments or line-delimited JSON-LD.
  - Integration: Exposed in Flask endpoints via `Response(stream_with_context(stream_collection_to_rdf(...)), mimetype=...)`.
- **Rationale**: Prevents high memory consumption when serializing large collections (e.g. 5,000+ items) which would otherwise exhaust container memory if materialized into a single in-memory `rdflib.Graph`.

### 6. Expanded Format Support & Content Negotiation
- **Decision**: Support three standardized formats:
  - `turtle`: `text/turtle`, `application/x-turtle`
  - `json-ld`: `application/ld+json`
  - `nt`: `application/n-triples`, `text/plain`
- **Rationale**: Conforms to W3C Linked Data Platform and HTTP Content Negotiation best practices, allowing simple streaming ingestion by external SPARQL triplestores using N-Triples.

## Risks / Trade-offs

- **[Risk: Memory spikes when serializing very large collections via monolithic endpoints]** → **Mitigation**: Introduce `stream_collection_to_rdf()` for streaming transfers, set default pagination limits on monolithic endpoints, and encourage chunked N-Triples exports.
- **[Risk: Missing or malformed metadata fields in legacy catalog entries]** → **Mitigation**: Defensive dictionary access and attribute checks in `_enrich_graph_from_db()`. Only emit triples when valid non-empty values exist; never crash on missing keys.
- **[Risk: Breaking FRBR ontological hierarchy when mapping flat Schema.org types]** → **Mitigation**: Enforce project rule that FRBR hierarchy is never bypassed (`Work -> Expression -> Manifestation -> Item`). `schema:isbn` is strictly attached to `Manifestation` (F3), never `Work` (F1).
- **[Risk: Prefix clashes across RDF formats]** → **Mitigation**: Standardize namespace bindings (`frbr`, `schema`, `sioc`, `prov`) uniformly across all serializers and JSON-LD contexts.

## Migration Plan

- All enhancements are additive and backward-compatible.
- Existing callers of `serialize_collection_to_rdf()` continue to function with improved performance and enriched triples.
- Public collection endpoints automatically supply richer metadata to existing clients without requiring client updates.
- Rollback: Reverting `app/core/frbr_service.py` and `app/api/public.py` returns serialization to prior minimal triple generation.
