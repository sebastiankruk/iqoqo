## Context

See `proposal.md` for motivation and background.

iqoqo catalogs books, board games, vinyl records, and digital media using the FRBR ontology (Work → Expression → Manifestation → Item) stored in PostgreSQL schemas (`catalog`, `inventory`, `auth`). Milestone v0.8.2 deliverable C14 (R13) introduces external Linked Open Data (LOD) entity linking and an asynchronous ETL pipeline to connect library catalog entities to DBpedia, WordNet, and GeoNames.

The existing codebase provides Celery task infrastructure via `app/core/celery_app.py` and `app/core/tasks.py` with Redis as the broker, and an extensible manifestation detail page at `frontend/app/manifestation/[id]/page.tsx`. This technical design defines the architecture for external LOD resolution clients, background task orchestration, relational semantic link storage adhering to FRBR boundaries, API endpoints, and the frontend manifestation UI.

## Goals / Non-Goals

**Goals:**
- Implement `app/core/lod_linking_service.py` with robust clients for DBpedia Lookup, WordNet synset mapping, and GeoNames geographic resolution.
- Enforce strict FRBR scoping: Work-level links for authors and intellectual works, Expression-level links for language/translators, Manifestation-level links for publishers, publication places, and format identifiers.
- Create a dedicated database model `SemanticLink` in `app/db/core.py` (table `catalog.semantic_links`) supporting entity polymorphism, external URIs, confidence scores, and verification status.
- Implement asynchronous Celery tasks (`link_manifestation_lod_task`, `batch_link_catalog_lod_task`) in `app/core/tasks.py` with rate limiting, timeouts, and Redis caching.
- Expose REST API endpoints under `/api/manifestations/<id>/semantic-links` to fetch links and trigger on-demand re-linking.
- Implement React component `frontend/components/manifestation/semantic-links.tsx` embedded in manifestation detail pages displaying authority badges and external previews.
- Ensure automated test coverage with mocked external API responses in `tests/test_lod_linking.py`.

**Non-Goals:**
- Running a self-hosted full-dump triplestore (e.g. local 100GB DBpedia or GeoNames mirror) — resolutions use public APIs with local Redis caching.
- Synchronous entity linking during HTTP request ingestion cycles — all external network queries are strictly asynchronous.
- Deep natural language processing (NLP) or full-text entity extraction — linking uses structured bibliographic fields (title, author, publisher, publication place, subject tags).
- Direct linking of Item entities (F4) — Items inherit semantic links from their parent Manifestation and Work.

## Decisions

### 1. Dedicated Relational Table (`catalog.semantic_links`) vs `meta` JSON
- **Decision**: Store resolved LOD links in a dedicated `catalog.semantic_links` table rather than embedding them directly in entity `meta` JSON.
  - Columns: `id` (int primary key), `entity_type` (varchar: `work`, `manifestation`, `contributor`), `entity_id` (int foreign key), `authority` (varchar: `dbpedia`, `wordnet`, `geonames`), `external_uri` (varchar 2048), `pref_label` (varchar 500), `confidence` (float), `match_strategy` (varchar: `exact`, `lookup`, `sparql`), `attributes` (jsonb for coordinates, synset IDs, etc.), `verified` (boolean), `created_at`, `updated_at`.
- **Rationale**: External LOD links require indexing by external URI (for reverse lookup and duplicate detection), cross-entity querying, and clear separation from user-entered metadata. First-class relational storage prevents metadata bloat and enforces FRBR entity relationships.
- **Alternatives considered**:
  - *Embedding in `Manifestation.meta`*: Rejected because author and subject links belong to the Work (F1), not Manifestation (F3). Duplicating them in manifestation JSON violates FRBR normalization and makes updating difficult.

### 2. Asynchronous Celery Tasks with Redis Caching
- **Decision**: Run all LOD reconciliation through Celery tasks (`link_manifestation_lod_task`) dispatched via `submit_task()`. Cache external API responses in Redis with a 24-hour TTL keyed by normalized entity query strings.
- **Rationale**: External LOD endpoints (DBpedia, GeoNames) frequently encounter network latency (500ms–2s) and rate limits. Celery ensures background execution without blocking user workflows, while Redis caching prevents duplicate outbound network calls for common publishers, authors, or places.
- **Alternatives considered**:
  - *In-process threading (`threading.Thread`)*: Rejected because unmanaged threads cannot be monitored across Gunicorn workers and risk termination during worker recycling.

### 3. DBpedia Lookup Service with SPARQL Fallback
- **Decision**: Query the DBpedia Lookup API (`https://lookup.dbpedia.org/api/search`) using text matching and type filtering (`dbo:Book`, `dbo:MusicalWork`, `dbo:Person`), falling back to DBpedia SPARQL (`https://dbpedia.org/sparql`) only when lookup yields no results or ambiguous candidates.
- **Rationale**: The Lookup API is purpose-built for fast keyword and prefix resolution with relevance scoring. DBpedia's SPARQL endpoint is prone to 503/504 timeouts under heavy load; using it only as a targeted fallback minimizes external query failures.
- **Alternatives considered**:
  - *SPARQL-first resolution*: Rejected due to high failure rate and latency on DBpedia public endpoints.

### 4. GeoNames Resolution for Publication Locations
- **Decision**: Resolve publication places (from `Manifestation.meta["publication_place"]` or parsed publisher string) via the GeoNames Search API (`api.geonames.org/searchJSON`), persisting canonical URIs (`https://sws.geonames.org/<id>/`), country codes, and coordinates.
- **Rationale**: GeoNames provides stable Linked Data URIs and geographic hierarchies widely adopted by national libraries. Storing coordinates enables future map-based discovery.
- **Alternatives considered**:
  - *OpenStreetMap Nominatim*: Rejected because GeoNames provides standard RDF identifiers and is the established standard for bibliographic cataloging (e.g., Library of Congress Authorities).

### 5. WordNet Synset Mapping for Subject Tags
- **Decision**: Map Work subject and genre tags to WordNet 3.1 synset URIs (`http://wordnet-rdf.princeton.edu/id/...` / DBpedia WordNet) using an internal lexical mapping dictionary with fallback to DBpedia WordNet categories.
- **Rationale**: Common literary genres and subject headings are static concepts. An internal mapping cache resolves tags instantly (<1ms) without external network dependency, falling back to external LOD lookups only for novel concepts.
- **Alternatives considered**:
  - *Querying online WordNet web servers per tag*: Rejected due to latency and availability issues of legacy academic servers.

### 6. Component-Driven Manifestation UI
- **Decision**: Build `frontend/components/manifestation/semantic-links.tsx` and integrate it into `frontend/app/manifestation/[id]/page.tsx` using shadcn `Badge`, `Card`, and Lucide icons (`ExternalLink`, `Globe`, `BookMarked`, `MapPin`).
- **Rationale**: Consistent with iqoqo's design language. Badges provide immediate visual context on external linkages without cluttering the primary bibliographic details.

## Risks / Trade-offs

- **[Risk] External API throttling or rate-limiting (HTTP 429)**
  - *Mitigation*: Celery tasks use exponential backoff (`autoretry_for=(RequestException,)`, `default_retry_delay=30`). Redis caches query results for 24 hours. Requests include a descriptive `User-Agent: iqoqo/0.8.2` header.
- **[Risk] False-positive entity matches (e.g., matching a book to a movie with identical title)**
  - *Mitigation*: Reconcile with media type and author context: filter DBpedia candidates by expected ontology classes (`dbo:Book` for texts, `dbo:MusicalWork` for audio). Store confidence score; provide manual unlink option.
- **[Risk] Violation of FRBR ontology boundaries**
  - *Mitigation*: Explicit validation in `lod_linking_service.py` ensuring author and subject links are bound to `Work` (F1), while publisher locations and ISBN/OCLC links are bound to `Manifestation` (F3).
- **[Risk] Offline / local-first deployments without Internet access**
  - *Mitigation*: Service gracefully skips external linking if offline or disabled in instance configuration (`ENABLE_LOD_LINKING=False`).

## Migration Plan

1. **Database Schema**:
   - Add table `catalog.semantic_links` via Alembic migration (`alembic/versions/xxxx_add_semantic_links.py`).
   - Add composite indexes on `(entity_type, entity_id)` and `(authority, external_uri)`.
2. **Backend Services & Workers**:
   - Deploy `app/core/lod_linking_service.py`.
   - Register Celery tasks in `app/core/tasks.py`.
   - Update manifestation creation and enrichment pipelines to enqueue `link_manifestation_lod_task`.
3. **Frontend Integration**:
   - Add semantic links hook and component to manifestation detail view.
4. **Rollback Strategy**:
   - Feature can be disabled instantly via environment variable `ENABLE_LOD_LINKING=false`.
   - Schema addition is strictly additive; dropping `catalog.semantic_links` leaves core FRBR entities unaffected.
