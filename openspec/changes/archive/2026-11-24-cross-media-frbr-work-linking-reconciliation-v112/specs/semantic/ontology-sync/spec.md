## ADDED Requirements

### Requirement: Cross-Media Work Relation and Candidate Ontology and SHACL Parity

The system SHALL maintain explicit OWL class declarations (`iqoqo:WorkRelation`, `iqoqo:WorkLinkCandidate`), property contracts (including `frbroo:R2_is_derivative_of` alignment, `iqoqo:sourceWork`, `iqoqo:targetWork`, `iqoqo:relationType`, candidate status/provenance properties), and SHACL `NodeShape` constraints (rejecting self-links where `sourceWork == targetWork` and enforcing controlled relation/status vocabularies) in `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`, enforced by `scripts/sync_ontology.py --check` without weakening `iqoqo:WorkExpansionLinkShape` or `iqoqo:ExpansionWorkShape`.

#### Scenario: Ontology sync check validates WorkRelation and WorkLinkCandidate contracts

- **GIVEN** synchronized `WorkRelation` and `WorkLinkCandidate` SQLAlchemy models, OWL declarations in `docs/ontology/iqoqo.ttl`, and SHACL shapes in `docs/ontology/iqoqo-shapes.ttl`
- **WHEN** `python scripts/sync_ontology.py --check` executes
- **THEN** the check MUST exit with status code `0`, confirming `WorkRelation`, `WorkLinkCandidate`, and existing `WorkExpansionLink` / `ExpansionWorkShape` contracts are all present with exact domain, range, and SHACL coverage.

#### Scenario: SHACL shape rejects self-referential WorkRelation graph

- **GIVEN** an RDF graph containing an `iqoqo:WorkRelation` whose `iqoqo:sourceWork` and `iqoqo:targetWork` reference the same `Work` IRI
- **WHEN** `shacl_service.validate_graph()` validates the graph against `docs/ontology/iqoqo-shapes.ttl`
- **THEN** validation MUST return `conforms=False` reporting the self-link constraint violation.
