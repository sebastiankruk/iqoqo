## 1. Schema.org Mapping & Relational Enrichment

- [x] 1.1 Implement `SCHEMA_TYPE_MAP` in `app/core/frbr_service.py` mapping FRBR `content_type` strings (`text`, `audiobook`, `music`, `movie`, `board_game`, `puzzle`) to Schema.org URIRefs (`Book`, `Audiobook`, `MusicAlbum`, `Movie`, `Game`, `Product`), verifying mappings with unit tests.
- [x] 1.2 Implement `_enrich_graph_from_db()` in `app/core/frbr_service.py` adding `schema:publisher`, `schema:inLanguage`, `schema:datePublished`, `schema:contributor`, `schema:image`, `prov:wasDerivedFrom`, `schema:isPartOf`, `schema:hasPart`, and collection root `schema:Collection` nodes, verifying with unit tests asserting triple existence.
- [x] 1.3 Add specialized domain mapping for Concerts (`schema:MusicEvent`, `schema:performer`, `schema:startDate`, `schema:location`) and Board Games (`schema:Game`, `schema:numberOfPlayers`) in `app/core/frbr_service.py`, verifying with domain-specific unit tests.

## 2. Query Optimization (MOD-FRBR-02)

- [x] 2.1 Refactor collection queries in `app/api/public.py` (`fetch_user_public_collection`, `fetch_shared_collection_by_token`) and collection loaders in `app/core/frbr_service.py` to use `joinedload()` / `selectinload()` eager loading across `Item -> Manifestation -> Expression -> Work`, verifying N+1 queries are eliminated using SQL query counting in tests.
- [x] 2.2 Add eager loading fallback in `serialize_collection_to_rdf()` to hydrate un-hydrated ORM instances in a single bulk query before graph serialization, verifying with unit tests on un-hydrated Item lists.

## 3. Streaming Serialization & Format Expansion

- [x] 3.1 Implement `stream_collection_to_rdf()` generator in `app/core/frbr_service.py` yielding serialized RDF chunks for Turtle, JSON-LD, and N-Triples (`nt`) formats without loading entire collections into memory, verifying with unit tests on chunked outputs.
- [x] 3.2 Update `serialize_collection_to_rdf()` to support `output_format="nt"` (N-Triples) alongside existing `turtle` and `json-ld` options, verifying with parse tests across all three formats.
- [x] 3.3 Update public collection endpoints in `app/api/public.py` (`/u/<username>/items`, `/share/<token>`) to support N-Triples content negotiation (`application/n-triples`, `text/plain`) and streaming chunked responses, verifying via client integration tests.

## 4. Test Coverage & Verification

- [x] 4.1 Create comprehensive test suite `tests/test_rdf_serialization.py` validating full FRBR triple coverage, Schema.org type mapping, relational enrichment, domain mappings, format serializations, and streaming chunk generation.
- [x] 4.2 Run full test suite with `pytest tests/test_rdf_serialization.py` and verify all tests pass with zero regressions.
