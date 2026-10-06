## 1. OWL Ontology & SHACL Shapes Ground Truth

- [x] 1.1 Update `docs/ontology/iqoqo.ttl` with post-v0.7.18 classes (`UserWorkIntent`, `ItemCustodyEvent`, `LoanRequest`, `ReadingRoadmap`, `RoadmapItem`, `Tag`, `ItemTag`, `SocialNote`, `EscalationRequest`, `EntityAuditLog`) and their properties, verifying syntax with `rdflib.Graph().parse()`.
- [x] 1.2 Update `docs/ontology/iqoqo-shapes.ttl` with SHACL `NodeShape` and `PropertyShape` definitions for post-v0.7.18 models, verifying syntax and constraint validation against sample graphs.

## 2. Core SHACL Validation Service

- [x] 2.1 Implement `app/core/shacl_service.py` with cached loading of default shapes and ontology graphs, implementing `validate_graph()` and verifying with unit tests on conforming and non-conforming RDF graphs.
- [x] 2.2 Implement `validate_rdf_string()` in `app/core/shacl_service.py` supporting Turtle and JSON-LD parsing, verifying with unit tests on serialized RDF payloads.

## 3. Ontology Synchronization Script & CI Integration

- [x] 3.1 Implement `scripts/sync_ontology.py` with CLI argument parsing, Turtle syntax validation, and SQLAlchemy model comparison logic.
- [x] 3.2 Add `--check` mode to `scripts/sync_ontology.py` exiting with code 0 on parity and code 1 with error reports on syntax failure or model drift, verifying execution via shell.
- [x] 3.3 Add automated test suite for SHACL service and sync script in `tests/test_ontology_sync.py`, verifying test suite passes under pytest.

## 4. Entity IRI Minting

- [x] 4.1 Implement `@property def iri(self) -> str` on `Work`, `Expression`, `Manifestation`, and `Item` models in `app/db/core.py`, generating canonical URIs for `@id` Linked Data fields.
- [x] 4.2 Add unit tests for FRBR entity `iri` generation in `tests/test_ontology.py`, verifying correct canonical URI formatting across all four FRBR levels.
