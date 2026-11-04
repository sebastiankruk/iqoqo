## 1. Ontology, SHACL Shapes & Format Taxonomy

- [ ] 1.1 Extend `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, and `docs/ontology/taxonomy.ttl` with LEGO classes/properties (`iqoqo:setNumber`, `iqoqo:pieceCount`, `iqoqo:minifigCount`, `iqoqo:buildStatus`, `iqoqo:missingPiecesCount`, `iqoqo:instructionsIncluded`).
- [ ] 1.2 Add `lego` category and physical format mappings (`standard_set`, `ucs_collector_set`, `technic_set`, `minifigure_series`, `polybag`) to `shared/format_mappings.yaml`, `app/core/format_normalizer.py`, and `frontend/types/taxonomy.ts`.
- [ ] 1.3 Update RDF serialization in `app/core/frbr_service.py` / `public_rdf.py` to emit LEGO F3 and F5 triples.

## 2. Verification & Tests

- [ ] 2.1 Verify `scripts/sync_ontology.py --check` passes with zero drift.
- [ ] 2.2 Author unit tests in `tests/test_format_normalizer_lego.py` and `tests/test_ontology_validation.py` verifying SHACL conformance and format normalization.
- [ ] 2.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
