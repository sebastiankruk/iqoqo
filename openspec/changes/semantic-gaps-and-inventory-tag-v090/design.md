## Context

See `proposal.md` for background and motivation.

The platform provides RDF serialization (`app/core/frbr_service.py`), external LOD linking (`app/core/lod_linking_service.py`), and series memberships (`app/db/contributions.py`), but these components are not fully linked together in RDF graph generation. Furthermore, the ground-truth OWL ontology and SHACL shapes in `docs/ontology/` have lagged behind recently added relational tables. Lastly, Item (F5) currently relies on Manifestation-level ISBNs/barcodes, which cannot uniquely distinguish physical copies on shelves or during inter-library loans.

## Goals / Non-Goals

**Goals:**
- Round-trip accepted `SemanticLink` records (DBpedia, GeoNames, WordNet) into `owl:sameAs` and `schema:sameAs` RDF triples.
- Round-trip `WorkSeriesMembership` records into `schema:partOfSeries` and `schema:position` RDF triples.
- Bring `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, and `scripts/sync_ontology.py` into complete parity with `SemanticLink`, `WorkSeriesMembership`, and `DuplicateCandidate`.
- Add `local_barcode` to `catalog.items` with a linear Alembic migration (revision length <= 32 chars), exposing it through backend APIs and frontend UI.

**Non-Goals:**
- Implementing ActivityPub federation endpoints, WebFinger, or HTTP Signatures (reserved for v0.9.0).
- Modifying LOD reconciliation matching algorithms or scoring strategies.
- Enforcing global uniqueness on `local_barcode` (different collectors or libraries may use overlapping sequential tags; scoping is per-instance/owner).

## Decisions

### 1. RDF Batch Serialization with Zero N+1 Queries
* **Decision**: Eagerly load `semantic_links` on `Manifestation` and `Work`, and `series_memberships` on `Work` in `_eager_load_items_fallback` and streaming RDF queries using SQLAlchemy 2.0 `selectinload`.
* **Rationale**: Materializing RDF graphs in batches of 50 items must not execute per-row queries. In-memory filtering ensures only links with `status == 'accepted'` are emitted.
* **Alternatives Considered**: Fetching semantic links on-demand during graph iteration (rejected: causes N+1 query explosion on large exports).

### 2. Dual LOD Identity Vocabularies (`owl:sameAs` and `schema:sameAs`)
* **Decision**: For every accepted semantic link, assert both `(entity_uri, OWL.sameAs, external_uri)` and `(entity_uri, SCHEMA.sameAs, external_uri)`.
* **Rationale**: `owl:sameAs` is the universal Semantic Web standard expected by SPARQL endpoints, LOD crawlers, and graph reasoners. `schema:sameAs` is the standard recognized by search engines and Schema.org consumers. Emitting both provides maximum interoperability.

### 3. Series RDF Representation
* **Decision**: Represent series membership as `(work_uri, SCHEMA.partOfSeries, series_uri)` along with `(work_uri, SCHEMA.position, Literal(sequence, datatype=XSD.integer))`.
* **Rationale**: Follows standard Schema.org CreativeWork series guidelines without requiring intermediate reified blank nodes when simple ordinal sequence suffices.

### 4. Item `local_barcode` Physical Identity Column
* **Decision**: Add `local_barcode = db.Column(db.String(64), nullable=True, index=True)` to `Item` in `app/db/core.py` via linear Alembic migration `v0_8_4_item_local_barcode`.
* **Rationale**: 64 characters accommodates Code 128, Code 39, QR code payload hashes, or alphanumeric inventory asset tags (e.g. `LIB-MAIN-004821`). Nullable allows untagged items. Indexed for fast scanner lookup.

### 5. Ground-Truth TBox Expansion
* **Decision**: Declare `:SemanticLink`, `:WorkSeriesMembership`, and `:DuplicateCandidate` in `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`. Update `MODEL_CLASS_MAP` and property contracts in `scripts/sync_ontology.py`.
* **Rationale**: Keeps ontology contracts strictly verified by CI (`make sync-ontology`) preventing silent schema drift.

## Risks / Trade-offs

- **[Risk] High volume of semantic links per entity causing bloated RDF responses**
  - *Mitigation*: Strictly filter `status == 'accepted'` (excluding `suggested` and `rejected` links). Typically 1-3 links per entity.
- **[Risk] Alembic revision identifier length overflow on Postgres**
  - *Mitigation*: Use revision name `v0_8_4_item_local_barcode` (25 chars), well below the 32-character `VARCHAR(32)` ceiling.
- **[Risk] UI clutter in ItemSidebar**
  - *Mitigation*: Render `local_barcode` in `SidebarIdentifiers` only when populated, alongside existing UPC/ISBN.
