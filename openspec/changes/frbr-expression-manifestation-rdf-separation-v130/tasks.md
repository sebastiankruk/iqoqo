## 1. RDF Expression/Manifestation Separation (`app/core/frbr_service.py`)

- [ ] 1.1 Move `schema:inLanguage`, `sioc:topic`, and live-concert `schema:MusicEvent` triples from `m_uri` to `e_uri` in `app/core/frbr_service.py`
- [ ] 1.2 Remove synthetic `expression_id = item_id` / `work_id = expression_id` IRI aliasing and recursively populate `seen_expressions` / `seen_manifestations` in `_enrich_graph_from_db` when serializing `Work` or `Expression`

## 2. Ingestion Tier Purity & Activity Ontology

- [ ] 2.1 Stop copying `publisher` onto `Work.meta` and `Authors`/`mechanics`/`work_kind`/`issn` onto `Manifestation.meta` during ingestion (`app/core/ingest.py`, `app/core/frbr_service.py`), plus add idempotent legacy cleanup script
- [ ] 2.2 Document/model `ReadingSession` and `ItemStatusLog` in `docs/ontology/iqoqo.ttl` / `iqoqo-shapes.ttl` and update SPARQL migration notes in `docs/SEMANTIC_WEB.md`

## 3. Tests & Verification

- [ ] 3.1 Update/add tests in `tests/test_rdf_serialization.py`, `tests/test_sparql_service.py`, and `tests/test_data_export.py` verifying strict `e_uri` vs `m_uri` triple subjects and full Work/Expression child enrichment
- [ ] 3.2 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, and `IQOQO_AI_MODE=1 make secret-scan`
