## ADDED Requirements

### Requirement: Canonical Entity Identity Across RDF Formats

Equivalent Work, Expression, Manifestation, and Item entities MUST use one canonical IRI policy across model helpers, public RDF, SPARQL graphs, Turtle, N-Triples, JSON-LD, and authenticated exports.

#### Scenario: Same entity exported in multiple formats

- **WHEN** the same collection is serialized as public RDF and authenticated JSON-LD/Turtle
- **THEN** equivalent FRBR entities resolve to the same canonical IRIs

#### Scenario: Relationship enrichment is shape-compatible

- **WHEN** contributor, part/whole, collection, and provenance triples are emitted
- **THEN** their RDF object/value types satisfy the canonical OWL/SHACL contract

### Requirement: Consistent FRBR Namespace Contract

RDF serializers MUST use the documented FRBR and iqoqo namespaces consistently and MUST not silently mix alternate class/property vocabularies for the same relationship.

#### Scenario: SHACL validation of enriched export

- **WHEN** an export contains contributors and relational enrichment
- **THEN** the complete graph passes the canonical SHACL validation or returns a deterministic validation failure during export testing
