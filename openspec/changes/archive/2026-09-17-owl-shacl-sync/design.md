## Context

See `proposal.md` for motivation and background.

iqoqo has stabilized its relational database schema across PostgreSQL schemas (`catalog`, `inventory`, `auth`, `social`, `config`) as of v0.7.18. The backend utilizes `rdflib` and `pyshacl` for Semantic Web processing, with initial ontology and SHACL shapes located in `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`. However, domain additions (e.g., user work intents, custody tracking, loan requests, reading roadmaps, social notes, custodian escalation, tags, and audit logging) are not yet fully modeled in the OWL ontology or constrained in SHACL shapes. Furthermore, SHACL validation is currently performed only in isolated tests without a centralized core service, and no automated CI mechanism exists to detect ontology drift.

## Goals / Non-Goals

**Goals:**
- Extend `docs/ontology/iqoqo.ttl` with OWL classes, object properties, and datatype properties corresponding to post-v0.7.18 database models.
- Extend `docs/ontology/iqoqo-shapes.ttl` with SHACL `NodeShape` and `PropertyShape` constraints for post-v0.7.18 models, enforcing relationship and cardinality invariants.
- Implement `app/core/shacl_service.py` exposing `validate_graph()` and `validate_rdf_string()` with in-memory caching of parsed shapes and ontology graphs.
- Implement `scripts/sync_ontology.py` with a CI-compatible `--check` flag that validates Turtle syntax and model-to-ontology completeness, exiting with code 0 on success or 1 on drift.
- Add stable `@property def iri(self) -> str` to `Work`, `Expression`, `Manifestation`, and `Item` models in `app/db/core.py` for canonical Linked Data `@id` generation.

**Non-Goals:**
- Implementing the public `/api/sparql` endpoint or SPARQL UI explorer (deferred to C2).
- Implementing complete JSON-LD content-negotiation responses for all REST endpoints (deferred to C3).
- Modifying underlying PostgreSQL schema definitions or adding Alembic migrations.
- ActivityPub federation actor profiles or inbox/outbox protocols (deferred to v0.9.0).

## Decisions

### 1. Direct Model-to-OWL Mapping in `iqoqo:` Namespace
- **Decision**: Map post-v0.7.18 SQLAlchemy models directly to OWL classes in `https://iqoqo.org/ontology#` (e.g., `iqoqo:UserWorkIntent`, `iqoqo:ItemCustodyEvent`, `iqoqo:LoanRequest`, `iqoqo:ReadingRoadmap`, `iqoqo:RoadmapItem`, `iqoqo:Tag`, `iqoqo:ItemTag`, `iqoqo:SocialNote`, `iqoqo:EscalationRequest`, `iqoqo:EntityAuditLog`).
- **Rationale**: Retains clear 1:1 semantics between relational database models and semantic graphs, making SPARQL queries and data exports intuitive.
- **Alternatives considered**: Relying purely on external ontologies (e.g. generic Schema.org or Dublin Core); rejected because iqoqo requires domain-specific FRBR hierarchy, custody tracking, and library loan states not expressible in flat schemas.

### 2. Centralized SHACL Service with Graph Caching
- **Decision**: Build `app/core/shacl_service.py` with cached graph loading for `iqoqo-shapes.ttl` and `iqoqo.ttl`. Expose two primary entry points:
  - `validate_graph(data_graph: Graph, shapes_graph: Optional[Graph] = None, ont_graph: Optional[Graph] = None, inference: str = "rdfs") -> tuple[bool, Graph, str]`
  - `validate_rdf_string(data_str: str, format: str = "turtle", ...) -> tuple[bool, Graph, str]`
- **Rationale**: Parsing Turtle files on every validation call introduces unnecessary disk and CPU overhead. Caching the parsed shapes and ontology graphs ensures fast execution in production and tests.
- **Alternatives considered**: Calling `pyshacl.validate` inline wherever needed; rejected due to code duplication and inconsistent validation parameters.

### 3. CI Parity Verification in `scripts/sync_ontology.py`
- **Decision**: Provide a dual-mode Python script:
  - Default mode: Parses and validates Turtle files, reports model coverage, and can format/sync definitions.
  - `--check` mode: Validates Turtle syntax and verifies that all registered core database entity types have corresponding OWL class definitions. If any syntax error or missing class is detected, prints actionable error logs to stderr and exits with status code 1.
- **Rationale**: Enables integration into CI pipelines (`pytest`, GitHub Actions, or pre-commit checks) to prevent future schema drift.
- **Alternatives considered**: Static linters; rejected because standard linters cannot verify parity against dynamic SQLAlchemy model registrations.

### 4. Canonical IRI Minting on FRBR Entities
- **Decision**: Implement `iri` property on `Work`, `Expression`, `Manifestation`, and `Item` returning `f"{base_url}/{entity_plural}/{self.id}"` (e.g., `https://iqoqo.org/works/1`). Base URL defaults to `https://iqoqo.org` and can be overridden by instance configuration or environment variables.
- **Rationale**: Provides consistent, dereferenceable URIs for `@id` fields across JSON-LD, RDF Turtle, and upcoming SPARQL query responses.
- **Alternatives considered**: URN-based identifiers (`urn:iqoqo:work:1`); rejected because Linked Open Data standards favor HTTP(S) dereferenceable URIs.

## Risks / Trade-offs

- **[Risk: SHACL validation performance overhead on large graphs]** → **Mitigation**: Use cached parsed shapes graphs and RDFS inferencing; validation can be executed asynchronously in Celery tasks or at boundaries rather than in hot database write loops.
- **[Risk: Ontology and schema drift during rapid feature development]** → **Mitigation**: Add `scripts/sync_ontology.py --check` to CI test execution so PRs failing parity checks cannot merge silently.
- **[Risk: Inconsistent IRI formats between different serialization endpoints]** → **Mitigation**: Make `model.iri` the single authoritative source for `@id` generation across serializers.
