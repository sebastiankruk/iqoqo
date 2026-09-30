## Why

The v0.8.0 release milestone requires exposing the iqoqo digital library catalog as Linked Open Data (LOD), RDF, and JSON-LD graphs, backed by an upcoming SPARQL query endpoint. Currently, `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl` lag behind database schema additions made through v0.7.18 (including user work intents, custody tracking, lending requests, roadmaps, social feedback, tags, and audit logging), lack automated CI sync verification, lack a reusable runtime SHACL validation service, and FRBR models lack uniform IRI minting for `@id` identifiers. Establishing the OWL ontology and SHACL shapes as synchronized ground truth with automated CI checks is necessary to guarantee semantic consistency before shipping public RDF endpoints.

## What Changes

- **Synchronize OWL Ontology (`docs/ontology/iqoqo.ttl`)**: Add OWL classes, object properties, and datatype properties representing DB schema entities and relationships introduced through v0.7.18 (e.g., `UserWorkIntent`, `ItemCustodyEvent`, `LoanRequest`, `ReadingRoadmap`, `RoadmapItem`, `Tag`, `ItemTag`, `SocialNote`, `EscalationRequest`, `EntityAuditLog`).
- **Synchronize SHACL Shapes (`docs/ontology/iqoqo-shapes.ttl`)**: Define SHACL `NodeShape` and `PropertyShape` constraints for post-v0.7.18 models, validating cardinalities, target classes, and relationship invariants.
- **Ontology Sync Script with CI Check Mode (`scripts/sync_ontology.py`)**: Implement an operational script capable of validating ontology syntax, verifying schema-to-ontology parity, and failing with non-zero exit codes in CI when invoked with `--check`.
- **Reusable SHACL Validation Service (`app/core/shacl_service.py`)**: Create a centralized core validation service providing `validate_graph()` and `validate_rdf_string()` methods backed by `pyshacl` with RDFS inferencing and cached default shapes.
- **Entity IRI Minting on FRBR Models**: Introduce a consistent `iri` property across `Work`, `Expression`, `Manifestation`, and `Item` models in `app/db/core.py` for canonical Linked Data `@id` generation.

## Capabilities

### New Capabilities
- `semantic/ontology-sync`: Synchronize OWL ontology and SHACL shapes with SQLAlchemy models, provide runtime SHACL validation service (`validate_graph`, `validate_rdf_string`), CI-compatible `--check` verification, and stable entity IRI minting on FRBR models.

### Modified Capabilities

## Impact

- **Ontology & Shapes**: `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl` updated with new classes, properties, and constraint shapes.
- **Backend Core**: `app/core/shacl_service.py` added; `app/db/core.py` updated with `iri` properties on `Work`, `Expression`, `Manifestation`, `Item`.
- **Scripts & CI**: `scripts/sync_ontology.py` added with `--check` mode; CI workflows or test suites can run check mode to guard against ontology drift.
- **Dependencies**: Uses existing `pyshacl` and `rdflib` dependencies already present in project environment.
- **Breaking Changes**: None. Additive properties and validation utilities.
