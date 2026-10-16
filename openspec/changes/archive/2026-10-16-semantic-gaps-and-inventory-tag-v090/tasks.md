## 1. Item Local Barcode Database & API

- [x] 1.1 Add `local_barcode` column (`db.String(64)`, nullable=True, index=True) to `Item` model in `app/db/core.py`.
- [x] 1.2 Create linear Alembic migration `v0_8_4_item_local_barcode` with single head lineage and verify with `flask db upgrade` / `pytest tests/test_migrations.py`.
- [x] 1.3 Update Item serialization `to_dict()` and `POST`/`PUT` endpoints in `app/api/items.py` to accept, validate, and return `local_barcode`.
- [x] 1.4 Add backend test suite in `tests/test_item_local_barcode.py` verifying item creation, retrieval, and updates with `local_barcode`.

## 2. RDF Serialization for External LOD Links & Series Memberships

- [x] 2.1 Update `app/core/frbr_service.py` (`build_collection_rdf_graph`) to serialize `status == 'accepted'` `SemanticLink` rows into `owl:sameAs` and `schema:sameAs` triples for Manifestation and Work entities.
- [x] 2.2 Update `app/core/frbr_service.py` to serialize `WorkSeriesMembership` rows into `schema:partOfSeries` and `schema:position` triples on Work entities.
- [x] 2.3 Ensure `selectinload` queries in `_eager_load_items_fallback` and streaming serializers fetch `semantic_links` and `series_memberships` without N+1 queries.
- [x] 2.4 Add unit tests in `tests/test_rdf_serialization.py` verifying `owl:sameAs`, `schema:sameAs`, and `schema:partOfSeries` emission and filtering of unverified links.

## 3. Ground-Truth Ontology & SHACL Synchronization

- [x] 3.1 Add OWL class declarations for `:SemanticLink`, `:WorkSeriesMembership`, and `:DuplicateCandidate` along with property definitions to `docs/ontology/iqoqo.ttl`.
- [x] 3.2 Add SHACL constraint shapes for the new classes and properties to `docs/ontology/iqoqo-shapes.ttl`.
- [x] 3.3 Update `MODEL_CLASS_MAP` and property contracts in `scripts/sync_ontology.py` and verify `python scripts/sync_ontology.py --check` passes with zero drift.

## 4. Frontend UI & Integration Verification

- [x] 4.1 Update `Item` interface in `frontend/types/frbr.ts` to include `local_barcode?: string | null`.
- [x] 4.2 Expose `local_barcode` in `frontend/components/item/sidebar/sidebar-identifiers.tsx` when present.
- [x] 4.3 Add `local_barcode` field to Item edit dialog / form in `frontend/components/item/edit-item-dialog.tsx`.
- [x] 4.4 Add frontend unit test coverage in `frontend/__tests__/components/item/sidebar/sidebar-identifiers.test.tsx` verifying local barcode display.
- [x] 4.5 Run full verification via `make lint` and `make test` to ensure clean CI compatibility.
