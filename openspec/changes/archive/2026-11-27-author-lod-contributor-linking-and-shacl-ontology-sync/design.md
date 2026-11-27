## Context

The `/ontologist-expert` audit confirmed `scripts/sync_ontology.py --check` only checks a subset of predicates and shapes. In practice, author DBpedia URIs sit on `SemanticLink(entity_type="work")` (creating `owl:sameAs` logical collapse across Works and stranding `Contributor` nodes), `iqoqo:*` SHACL shapes target `iqoqo:Manifestation`/`Item` while RDF exports emit `frbr:Manifestation`/`Item`, and newly added domain features (`physicalLocation`, `SerialWork`/`PublicationIssue`, `ContainerAggregation` details, `ImageScan`, `matrixRunout`, `custodyHolder`) lack complete OWL/SHACL coverage.

## Goals / Non-Goals

- **Goals:**
  - Eliminate `owl:sameAs` author/work identity collapse by attaching author `SemanticLink`s strictly to `Contributor` (`entity_type="contributor"`) with dereferenceable contributor IRIs and safe backfill.
  - Ensure all emitted RDF terms and `Serial`/`LEGO`/`Cartographic`/`Item.physicalLocation`/`ContainerAggregation`/`ImageScan` structures are declared in `iqoqo.ttl`, enforced in `sync_ontology.py`, and validated by `iqoqo-shapes.ttl` in tests.
  - Prevent future FRBR tier drift on `Work.meta` / `Manifestation.meta` / `Item.meta` mutations.
- **Non-Goals:**
  - Moving `Expression`-level RDF predicates (`schema:inLanguage`, `sioc:topic`, `schema:MusicEvent`) off `m_uri` to `e_uri` (breaking change deferred cleanly to `C170` in `v1.3.0`).

## Decisions

1. **Author LOD Ownership (`entity_type="contributor"`):**
   - `lod_linking_service.py:1407-1441` resolves or creates a `Contributor` + `WorkContribution` (`role="author"`) and stores `SemanticLink(entity_type="contributor", entity_id=contributor.id, ...)`.
   - Retrieval (`Manifestation.get_semantic_links`), curation (`PATCH`/`DELETE /api/manifestations/<id>/semantic-links`), filters (`CatalogFilterBuilder._apply_lod`), admin telemetry (`get_lod_stats`, `cleanup_lod_links_task`), and frontend badges surface `contributor`-tier links transparently across shared works.
   - Idempotent backfill script migrates legacy `(entity_type="work", role="author" / dbo:Person)` links onto `Contributor`, deduplicating conflicts (`verified=True` > `accepted` > `suggested` > highest confidence) and logging `EntityAuditLog` entries.
2. **OWL/SHACL Activation Without Breaking External Type Queries:**
   - Emit both `frbr:Manifestation`/`iqoqo:Manifestation` and `frbr:Item`/`iqoqo:Item` (plus declare `iqoqo:Work/Expression/Manifestation/Item` `rdfs:subClassOf` / `owl:equivalentClass` in `iqoqo.ttl`) so both existing FRBR queries and `iqoqo:Lego*Shape`/`Cartographic*Shape`/`SerialWorkShape`/`PublicationIssueShape` execute cleanly.
   - Add `iqoqo:physicalLocation` (`sh:maxCount 0` on Work/Manifestation) and `"expression"` on `SemanticLinkShape`.
3. **Strict Mutation Guards:**
   - Remove arbitrary `Work.meta` / `Item.meta` format duplication in `update_manifestation` & `update_frbr_entity_type`, and reject/strip non-Item mutations of `Manifestation.meta` from `/api/items/<id>` unless explicitly scoped.
