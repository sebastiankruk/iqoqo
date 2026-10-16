## Why

Before closing the v0.8.x release stream and proceeding to v0.9.0 ActivityPub federation, an architectural and ontological review identified four critical semantic and provenance gaps:
1. External Linked Open Data (LOD) authorities (DBpedia, GeoNames, WordNet) captured in `catalog.semantic_links` are not emitted as `owl:sameAs` / `schema:sameAs` triples in public RDF exports and SPARQL graphs, leaving reconciled LOD knowledge trapped in PostgreSQL.
2. Series memberships introduced in v0.8.4 (`catalog.work_series_memberships`) lack RDF serialization (`schema:partOfSeries`) and are absent from the ground-truth OWL ontology (`docs/ontology/iqoqo.ttl`) and SHACL shapes.
3. Ground-truth ontology contracts in `docs/ontology/iqoqo.ttl` and `scripts/sync_ontology.py` have drifted behind the relational schema by omitting `SemanticLink`, `WorkSeriesMembership`, and `DuplicateCandidate`.
4. The `Item` (F5) model lacks a `local_barcode` / `inventory_tag` attribute distinct from Manifestation-level ISBN/UPC barcodes, creating an ontological blocker for tracking individual physical exemplars across physical shelves and federated inter-library loans.

Closing these gaps now preserves FRBR ontological purity, ensures complete LOD round-tripping, and establishes the physical item identity model required for v0.9.0 federation.

## What Changes

- **LOD RDF Export**: Extend `app/core/frbr_service.py` (`build_collection_rdf_graph` and entity serializations) to emit `owl:sameAs` and `schema:sameAs` triples referencing external authority URIs for all `accepted` `SemanticLink` rows.
- **Series RDF Export**: Extend Work serialization in `app/core/frbr_service.py` to emit `schema:partOfSeries` (or `schema:Series` nodes with `schema:position`) for each linked series membership.
- **Ontology & SHACL Parity**: Add OWL class and property declarations for `:SemanticLink`, `:WorkSeriesMembership`, and `:DuplicateCandidate` to `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`; update `MODEL_CLASS_MAP` and property validation contracts in `scripts/sync_ontology.py`.
- **Physical Item Local Barcode**: Add `local_barcode` (`VARCHAR(64)`, indexed, nullable) column to `catalog.items` via a linear Alembic migration; expose `local_barcode` across Item serialization, creation/update API endpoints, Item sidebar/header views, and the manual entry / item edit forms.

## Capabilities

### New Capabilities
- `item-local-barcode`: Adds physical exemplar identifier (`local_barcode` / `inventory_tag`) to Item (F5) model, distinct from Manifestation-level EAN/UPC/ISBN, supporting physical shelf stickers and circulation scanning.

### Modified Capabilities
- `semantic/rdf-serialization`: Enrich RDF graph generation to serialize accepted external LOD semantic links as `owl:sameAs` / `schema:sameAs` triples, and serialize `WorkSeriesMembership` records into `schema:partOfSeries` structures with sequence numbers.
- `semantic/ontology-sync`: Synchronize `iqoqo.ttl`, `iqoqo-shapes.ttl`, and `scripts/sync_ontology.py` with `SemanticLink`, `WorkSeriesMembership`, and `DuplicateCandidate` relational entities.

## Impact

- **Database**: Add `local_barcode` column to `catalog.items` via linear Alembic migration `v0_8_4_item_local_barcode`.
- **Backend APIs**:
  - `GET /api/items/<id>`, `POST /api/items`, `PUT /api/items/<id>` accept and expose `local_barcode`.
  - `/api/public/works/<id>`, `/api/public/manifestations/<id>`, `/api/public/items/<id>`, and `/api/sparql` serialize `sameAs` and `partOfSeries` triples.
- **Ontology & Scripts**: `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, and `scripts/sync_ontology.py` reflect the expanded contract.
- **Frontend**: Item detail sidebar identifiers (`SidebarIdentifiers`) and Item edit dialog display and edit `local_barcode`.
