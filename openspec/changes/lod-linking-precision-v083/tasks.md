## 1. Schema Migration & Data Model

- [x] 1.1 Create Alembic migration adding `status` column to `semantic_links` table with default `'accepted'` (revision id <= 32 chars) and verify linear heads via `alembic heads`
- [x] 1.2 Update `SemanticLink` SQLAlchemy model in `app/db/core.py` with `status` enum/string column and verify model instantiation in tests

## 2. Precision Scoring & Ontological Class Filters

- [x] 2.1 Implement composite score calculation in `app/core/lod_linking_service.py` incorporating label similarity, creator/year corroboration, and rank margin; verify with unit test in `tests/test_lod_linking.py`
- [x] 2.2 Add strict ontology class filtering in `DBpediaClient` (Work subtypes, Person/Org) and GeoNames featureClass (`P`), rejecting disambiguation pages; verify against mock response fixtures
- [x] 2.3 Integrate dual thresholds (`LOD_AUTO_APPLY_THRESHOLD` and `LOD_SUGGESTION_THRESHOLD`) via `ConfigService` and verify candidates are tagged `accepted` or `suggested`

## 3. API & Filter Enforcement

- [x] 3.1 Update `/api/manifestations/<id>/semantic-links` to return link `status` and add accept/reject PATCH endpoint; verify with pytest in `tests/test_lod_linking_api.py`
- [x] 3.2 Update `CatalogFilterBuilder` and collection queries to filter by `status == 'accepted'`, ignoring suggested/rejected links; verify query outputs in filter tests
- [x] 3.3 Ensure RDF/SPARQL serialization export pipelines only include `accepted` links; verify with serialization unit tests

## 4. UI Dashboard & Cleanup ETL

- [x] 4.1 Update `/admin/lod` dashboard cards to display suggested link counts and add dry-run cleanup button; verify with frontend Vitest tests
- [x] 4.2 Implement background cleanup task in `app/core/tasks.py` re-scoring existing links and logging demotions to `EntityAuditLog`; verify dry-run and apply modes via pytest
- [x] 4.3 Add precision regression fixture test suite with known true/false positive pairs and verify regression gate passes in CI
