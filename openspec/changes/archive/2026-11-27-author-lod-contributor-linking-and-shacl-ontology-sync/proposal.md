## Why

A `/ontologist-expert` FRBR / Semantic Web audit revealed critical ontological defects in LOD author modeling, OWL/SHACL alignment, and RDF export guardrails:

1. **Author DBpedia `SemanticLink`s Pollute `Work` Identities (`app/core/lod_linking_service.py:1407-1441`):** Author resolution via `DBpediaClient.resolve_person(...)` stores `SemanticLink(entity_type="work", entity_id=work.id, attributes={"role": "author", ...})` on every `Work` instead of attaching once to `Contributor` (`entity_type="contributor"`). RDF export then asserts `<works/42> owl:sameAs <dbpedia:Stephen_King>`, causing logical identity collapse across distinct Works by the same author, leaving `Contributor` nodes orphaned in RDF (`frbr_service.py` emits anonymous blank nodes for authors), and multiplying duplicate rows across Works.
2. **OWL/SHACL Class Disconnect & Missing Property Declarations:**
   - `docs/ontology/iqoqo.ttl` & `docs/ontology/iqoqo-shapes.ttl` omit `iqoqo:physicalLocation` (`C157`), `iqoqo:matrixRunout`, `iqoqo:custodyHolder`, `ContainerAggregation` properties (`componentName`, `quantity`), `ImageScan` properties / cover provenance, `taxonomy.ttl` vocabulary terms, and Serial shapes (`SerialWorkShape`, `PublicationIssueShape`).
   - `frbr_service.py` emits `rdf:type frbr:Manifestation` / `frbr:Item` rather than `iqoqo:Manifestation` / `iqoqo:Item` (and `iqoqo.ttl` only links `iqoqo:*` to `frbroo:*`, never `frbr:*`), so `LegoManifestationShape`, `LegoItemShape`, `CartographicManifestationShape`, and `CartographicItemShape` fail to trigger on general catalog exports. `ContainerAggregation` is flattened to `schema:hasPart`, bypassing `ContainerAggregationShape`.
   - `iqoqo-shapes.ttl` has typoed `frbr:` error messages (actual `sh:path frbrer:*`), omits `"expression"` from `SemanticLinkShape`, and `tests/test_data_export.py` validates SHACL only on two simple books.
3. **Ongoing `Work`/`Item` Meta Tier Drift & Sparse `SEMANTIC_WEB.md` Examples:** `update_manifestation` / `update_frbr_entity_type` copy `type`/`format`/`Format` onto `Work.meta` and `Item.meta`; `_update_physical_item` (`items.py:942-950`) lets item updates write arbitrary extras onto shared `Manifestation.meta`; `docs/SEMANTIC_WEB.md` SPARQL examples use stale `dc:title`/`frbr:` predicates instead of emitted `schema:name`/`frbrer:*`.

## What Changes

- **Author LOD Migration to `Contributor` (`app/core/lod_linking_service.py`, `frbr_service.py`, `filters.py`, `admin.py`, `manifestations.py`, `tasks.py`, frontend UI):**
  - Attach author DBpedia links to `Contributor` (`entity_type="contributor"`, creating/linking `WorkContribution` if missing), update `Manifestation.get_semantic_links`, semantic-link curation endpoints, LOD filters/stats, cleanup tasks, and `semantic-links.tsx` badges, and emit dereferenceable `<base_url>/contributors/<id>` IRIs instead of BNodes.
  - Provide an idempotent backfill script/migration moving existing `"work"` author links onto `Contributor` (with `EntityAuditLog` provenance and deduplication).
- **Ontology & SHACL Synchronization (`docs/ontology/`, `scripts/sync_ontology.py`, `frbr_service.py`, `tests/`):**
  - Declare `iqoqo:physicalLocation`, `iqoqo:matrixRunout`, `iqoqo:custodyHolder`, `ContainerAggregation` properties, `ImageScan` properties + cover provenance, `taxonomy.ttl` classes/predicates, `SerialWorkShape`, `PublicationIssueShape`, `physicalLocation` anti-leak `maxCount 0` constraints on Work/Manifestation, and link `iqoqo:*` <-> `frbr:*` (`rdfs:subClassOf` / dual `rdf:type`).
  - Reify `ContainerAggregation` in `_enrich_graph_from_db`, stop writing `type`/`format`/`Format` onto `Work.meta`/`Item.meta` and stop `ItemUpdateSchema` extras from mutating `Manifestation.meta`, update `docs/SEMANTIC_WEB.md` SPARQL queries, and expand SHACL validation in `tests/test_data_export.py` across LEGO, Maps, Serials, Audio, `physical_location`, `ImageScan`, `ContainerAggregation`, and `ExportService`.

## Impact

- Affected files: `app/core/lod_linking_service.py`, `app/core/frbr_service.py`, `app/api/filters.py`, `app/api/admin.py`, `app/api/manifestations.py`, `app/api/items.py`, `app/core/tasks.py`, `app/db/core.py`, `frontend/components/manifestation/semantic-links.tsx`, `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, `scripts/sync_ontology.py`, `docs/SEMANTIC_WEB.md`, backfill script/migration, and ontology/SHACL tests.
