## ADDED Requirements

### Requirement: Expanded Model Class Mapping and Property Parity

The system SHALL maintain explicit OWL class declarations, property contracts, and SHACL constraint shapes for `SemanticLink`, `WorkSeriesMembership`, and `DuplicateCandidate` in `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`, and enforce parity via `scripts/sync_ontology.py`.

#### Scenario: Running ontology sync check with expanded domain entities
- **WHEN** `python scripts/sync_ontology.py --check` is executed
- **THEN** `SemanticLink`, `WorkSeriesMembership`, and `DuplicateCandidate` are validated as mapped classes with valid OWL domains, ranges, and SHACL shapes.

#### Scenario: Detecting drift on unmapped new properties
- **WHEN** a property in the mapped contract for `SemanticLink` or `WorkSeriesMembership` is missing from `iqoqo.ttl`
- **THEN** `scripts/sync_ontology.py --check` fails with an explicit drift diagnostic.
