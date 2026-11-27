# author-lod-and-shacl-ontology-sync Specification

## Purpose
Separate `Contributor` LOD identities from `Work` identities to eliminate `owl:sameAs` collapse, synchronize `iqoqo.ttl` and `iqoqo-shapes.ttl` with all emitted FRBR/v1.2.0 RDF predicates, and enforce multi-domain SHACL validation.

## Requirements

### Requirement: Author LOD Attachment Strictly on Contributor

Author LOD links MUST be attached to `Contributor` (`entity_type="contributor"`) rather than `Work` (`entity_type="work"`), with dereferenceable contributor IRIs in RDF export and idempotent migration of legacy rows.

#### Scenario: Linking and exporting an author's DBpedia URI

- **GIVEN** a `Work` by `"Stephen King"` resolved via `DBpediaClient.resolve_person`
- **WHEN** LOD linking runs and RDF/JSON-LD is serialized for the Work or Collection
- **THEN** the `SemanticLink` MUST be stored with `entity_type="contributor"` on the `Contributor` record
- **AND** `owl:sameAs` / `schema:sameAs` MUST attach to `<base_url>/contributors/<id>` rather than `<base_url>/works/<id>`

### Requirement: Complete OWL Declarations and Active SHACL Shapes

All predicates emitted by `frbr_service.py` / `export_service.py` and vocabulary terms in `taxonomy.ttl` MUST be declared in `iqoqo.ttl`, registered in `scripts/sync_ontology.py`, and validated by `iqoqo-shapes.ttl`.

#### Scenario: Validating heterogeneous domain exports against SHACL

- **GIVEN** exported RDF/JSON-LD graphs containing LEGO sets, Cartographic maps, Serials (`SerialWork`/`PublicationIssue`), Audio (`matrixRunout`), `Item.physical_location`, `ContainerAggregation`, `ImageScan`, and `custodyHolder`
- **WHEN** `validate_graph()` runs against `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`
- **THEN** domain-specific shapes (`Lego*Shape`, `Cartographic*Shape`, `SerialWorkShape`, `PublicationIssueShape`, `ContainerAggregationShape`) MUST trigger actively and pass validation, while `iqoqo:physicalLocation` MUST be forbidden (`maxCount 0`) on `Work` and `Manifestation`

### Requirement: Prevention of Work and Item Meta Tier Drift

Editing a `Manifestation` or physical `Item` MUST NOT copy carrier formats onto `Work.meta` / `Item.meta` or silently overwrite shared `Manifestation.meta` from item-scoped endpoints.

#### Scenario: Updating an Item or Manifestation without polluting adjacent FRBR tiers

- **GIVEN** a collector updates physical attributes on an `Item` or edits a `Manifestation`'s format
- **WHEN** `PATCH /api/items/<id>` or `update_manifestation` persists changes
- **THEN** carrier formats MUST NOT be duplicated onto `Work.meta` or `Item.meta`, and item updates MUST NOT mutate shared `Manifestation.meta` fields
