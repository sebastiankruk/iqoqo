## 1. Database Model & Migrations

- [x] 1.1 Create `SemanticLink` model in `app/db/core.py` (supporting entity_type, entity_id, authority, external_uri, pref_label, confidence, match_strategy, attributes, verified, and timestamps) and generate Alembic migration for `catalog.semantic_links` table with composite indexes. Verify migration applies cleanly with `alembic upgrade head`.
- [x] 1.2 Implement helper relationship and query methods on `Work` and `Manifestation` models in `app/db/core.py` to retrieve associated semantic links adhering strictly to FRBR scoping rules. Verify with unit tests checking entity link retrieval.


## 2. LOD Resolution Service Engine

- [x] 2.1 Implement `DBpediaClient` in `app/core/lod_linking_service.py` supporting DBpedia Lookup API queries with media-category class filtering (`dbo:Book`, `dbo:MusicalWork`, `dbo:Person`), SPARQL fallback, and Redis caching. Verify with unit tests mocking DBpedia HTTP responses.
- [x] 2.2 Implement `GeoNamesClient` in `app/core/lod_linking_service.py` to resolve publisher locations and publication places to canonical GeoNames URIs with coordinate extraction and 24-hour Redis caching. Verify with unit tests mocking GeoNames JSON responses.
- [x] 2.3 Implement `WordNetMapper` in `app/core/lod_linking_service.py` to map subject and genre tags to canonical WordNet 3.1 synset URIs using local dictionary lookup and DBpedia WordNet category fallbacks. Verify with unit tests covering matching tags and fallback behavior.
- [x] 2.4 Implement `resolve_manifestation_links()` in `app/core/lod_linking_service.py` orchestrating DBpedia, WordNet, and GeoNames resolutions, filtering duplicate links, and persisting `SemanticLink` rows with strict FRBR scoping. Verify with unit tests ensuring Work-level vs Manifestation-level link separation.


## 3. Background ETL & Celery Tasks

- [x] 3.1 Implement Celery task `link_manifestation_lod_task(manifestation_id)` in `app/core/tasks.py` with exponential backoff retries (`autoretry_for`), execution timeouts, and task status tracking. Verify task execution with mock Celery worker test.
- [x] 3.2 Implement collection-level batch reconciliation task `batch_link_catalog_lod_task(manifestation_ids)` in `app/core/tasks.py` with chunking and rate-limit throttling. Verify batch task execution with unit tests.
- [x] 3.3 Hook asynchronous task dispatch into manifestation creation and enrichment pipelines so newly created or refreshed manifestations automatically trigger background LOD resolution. Verify trigger with integration tests.


## 4. REST API Endpoints

- [x] 4.1 Implement `GET /api/manifestations/<id>/semantic-links` in `app/api/manifestations.py` returning grouped LOD links (DBpedia, GeoNames, WordNet) with confidence scores and verification status. Verify with API test asserting HTTP 200 and expected JSON structure.
- [x] 4.2 Implement `POST /api/manifestations/<id>/semantic-links/relink` in `app/api/manifestations.py` to trigger on-demand background linking returning 202 Accepted with the Celery task ID. Verify endpoint triggers task and returns task ID.
- [x] 4.3 Implement `DELETE /api/manifestations/<id>/semantic-links/<link_id>` in `app/api/manifestations.py` allowing authorized users to dismiss or remove an incorrect semantic link. Verify endpoint deletes link and returns 204 No Content.


## 5. Manifestation Detail Page UI

- [x] 5.1 Implement React component `frontend/components/manifestation/semantic-links.tsx` with authority badges (DBpedia, GeoNames, WordNet), confidence indicators, and external link-outs (`target="_blank"`, `rel="noopener noreferrer"`). Verify component renders correctly in unit tests.
- [x] 5.2 Integrate `SemanticLinks` component into `frontend/app/manifestation/[id]/page.tsx` with API hook `useSemanticLinks(manifestationId)`, loading skeletons, and an on-demand "Scan External LOD" action button. Verify UI integration visually on manifestation detail view.
- [x] 5.3 Add internationalization strings for semantic links, authorities, and status tooltips in `frontend/messages/en.json` and `frontend/messages/pl.json`. Verify translations resolve properly.


## 6. Integration Testing & Verification

- [x] 6.1 Create comprehensive test suite in `tests/test_lod_linking.py` covering DBpedia, GeoNames, and WordNet client mocking, Celery task execution, rate-limit retries, and API endpoints. Verify all tests pass with `pytest tests/test_lod_linking.py`.
- [x] 6.2 Run frontend type checking and linting to verify frontend semantic link components compile without type errors.
