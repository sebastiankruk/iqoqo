## 1. Author LOD Migration to Contributor

- [x] 1.1 Update `app/core/lod_linking_service.py:1407-1441` to resolve/create `Contributor` + `WorkContribution` and attach author `SemanticLink` rows with `entity_type="contributor"`
- [x] 1.2 Update `Manifestation.get_semantic_links`, `get_manifestation_semantic_links_dict`, `/api/manifestations/<id>/semantic-links` PATCH/DELETE, `CatalogFilterBuilder._apply_lod`, `get_lod_stats`, `cleanup_lod_links_task`, and `frontend/components/manifestation/semantic-links.tsx` for `contributor`-tier links
- [x] 1.3 Emit dereferenceable `<base_url>/contributors/<id>` IRIs instead of author blank nodes in `app/core/frbr_service.py` (with `owl:sameAs`/`schema:sameAs` on contributor IRI) and add an idempotent backfill/dedup migration/script for legacy `"work"` author links

## 2. Ontology & SHACL Synchronization & Tier Purity Guards

- [x] 2.1 Declare `iqoqo:physicalLocation`, `iqoqo:matrixRunout`, `iqoqo:custodyHolder`, `ContainerAggregation` properties (`componentName`, `quantity`), `ImageScan` properties/provenance, and `taxonomy.ttl` terms in `docs/ontology/iqoqo.ttl` + link `iqoqo:*` <-> `frbr:*` classes
- [x] 2.2 Update `docs/ontology/iqoqo-shapes.ttl` (`SerialWorkShape`, `PublicationIssueShape`, `physicalLocation` `maxCount 0` on Work/Manifestation, `"expression"` in `SemanticLinkShape`, `frbr:`->`frbrer:` message fixes) and `scripts/sync_ontology.py` (`MAPPED_PROPERTY_CONTRACT`, `REQUIRED_SHAPE_CONTRACT`)
- [x] 2.3 Reify `ContainerAggregation` nodes in `_enrich_graph_from_db`, stop duplicating `type`/`format`/`Format` onto `Work.meta`/`Item.meta`, prevent `ItemUpdateSchema` extras mutating shared `Manifestation.meta`, and update `docs/SEMANTIC_WEB.md` SPARQL examples

## 3. Tests & Verification

- [x] 3.1 Expand `tests/test_data_export.py` & `tests/test_serial_ontology.py` to run `validate_graph()` on LEGO, Maps, Serials, Audio, `physical_location`, `ImageScan`, `ContainerAggregation`, `ExportService`, and SPARQL graphs
- [x] 3.2 Add/update tests in `tests/test_lod_linking.py`, `tests/test_lod_linking_api.py`, `tests/test_rdf_serialization.py`, and author backfill tests
- [x] 3.3 Run `IQOQO_AI_MODE=1 .venv/bin/python scripts/sync_ontology.py --check`, `make lint`, `make test-parallel`, and `make secret-scan`
