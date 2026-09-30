## Why

In milestone v0.8.2 (Linked Data Extensions & Performance, deliverable C14), iqoqo catalog entities (Works, Manifestations, and Contributors) exist largely as internal graph nodes without bidirectional links to the global Linked Open Data (LOD) cloud. To enrich catalog metadata automatically, support semantic browsing, and enable interoperability with external knowledge bases, iqoqo requires an asynchronous ETL linking service to discover, reconcile, and store links to DBpedia (for works, authors, and subjects), WordNet (for topic/genre synsets), and GeoNames (for publication places).

## What Changes

- **External LOD Resolution Engine (`app/core/lod_linking_service.py`)**:
  - DBpedia Lookup & SPARQL reconciliation matching Works and Contributors to canonical DBpedia resource URIs (`http://dbpedia.org/resource/...`).
  - WordNet concept mapping linking topical tags and subjects to formal WordNet lexical URIs.
  - GeoNames API resolution linking publisher locations and publication places on Manifestations to GeoNames entity URIs (`https://sws.geonames.org/...`).
- **Asynchronous ETL Pipeline & Celery Tasks**:
  - Background Celery task `link_manifestation_lod_task` (and collection-level batch task) to process external API resolutions asynchronously without blocking HTTP requests.
  - Caching and rate limiting layer to prevent external provider throttling and ensure idempotent re-linking.
  - Automatic task dispatch triggered after manifestation creation, enrichment, or metadata refetch.
- **FRBR-Compliant Semantic Link Persistence**:
  - Dedicated semantic links model (`catalog.semantic_links`) associating external URIs with proper FRBR hierarchy levels (Work-level topics/creators, Expression-level languages, Manifestation-level publishers and locations).
  - Preservation of confidence score, match strategy, and verification state (auto-linked vs user-verified).
- **Semantic Links API**:
  - REST endpoints at `/api/manifestations/<id>/semantic-links` to inspect linked entities and trigger background re-linking.
- **Manifestation Detail Page UI**:
  - Interactive semantic links component (`frontend/components/manifestation/semantic-links.tsx`) displaying badges and external previews for DBpedia entities, GeoNames publisher locations, and WordNet topics.

## Capabilities

### New Capabilities
- `semantic/lod-linking`: Asynchronous Linked Open Data (LOD) entity linking and ETL pipeline resolving library catalog items to DBpedia, WordNet, and GeoNames URIs with background Celery tasks, FRBR-compliant link storage, and manifestation detail UI.

### Modified Capabilities

## Impact

- **Backend Core**: New module `app/core/lod_linking_service.py` with DBpedia, WordNet, and GeoNames clients; task definitions in `app/core/tasks.py`.
- **Backend APIs**: New endpoints in `app/api/manifestations.py` under `/api/manifestations/<id>/semantic-links`.
- **Database Schema**: New table `catalog.semantic_links` with foreign keys to FRBR entities, or structured persistence in `meta` with database migration.
- **Frontend**: New UI component `frontend/components/manifestation/semantic-links.tsx` embedded in `frontend/app/manifestation/[id]/page.tsx`, updated API hooks and TypeScript definitions.
- **External Integration & Telemetry**: Outbound HTTP queries to DBpedia and GeoNames with timeout guardrails, circuit breakers, and user-agent compliance.
