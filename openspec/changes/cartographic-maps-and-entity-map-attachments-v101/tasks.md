## 1. Ontology, Format Taxonomy & Backend Map Attachments (`app/`)

- [ ] 1.1 Extend `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, `docs/ontology/taxonomy.ttl`, and `shared/format_mappings.yaml` with standalone `cartographic_map` / `atlas` formats (`iqoqo:mapScale`, `iqoqo:mapProjection`) and `iqoqo:hasMapAttachment` (`frbroo:R15_has_part`) + `iqoqo:mapInsertPresent`.
- [ ] 1.2 Add API support in `app/api/manifestations.py` and `app/api/items.py` to upload/attach/remove map supplements (`has_map`, `map_attachments` list with validated image uploads) on Manifestations and update `map_insert_present` on Items.
- [ ] 1.3 Extend `app/core/meta_display.py` and RDF serialization (`app/core/frbr_service.py`) to expose map attachments and standalone cartographic metadata.

## 2. Verification & Tests

- [ ] 2.1 Verify `scripts/sync_ontology.py --check` passes.
- [ ] 2.2 Author backend tests in `tests/test_maps_and_attachments.py` covering standalone cartographic map creation, attaching a map supplement to a Book/Game `Manifestation`, Item `map_insert_present` updates, and RDF serialization.
- [ ] 2.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
