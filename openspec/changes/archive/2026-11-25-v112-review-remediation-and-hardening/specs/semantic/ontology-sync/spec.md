## ADDED Requirements

### Requirement: OWL Domain Disjointness Between Reified WorkRelation and F1_Work

In `docs/ontology/iqoqo.ttl`, `iqoqo:sourceWork` (`rdfs:domain iqoqo:WorkRelation`, `rdfs:range frbroo:F1_Work`) SHALL NOT declare `rdfs:subPropertyOf frbroo:R2_is_derivative_of` (`rdfs:domain frbroo:F1_Work`), preserving clean OWL RDFS domain separation between the reified `iqoqo:WorkRelation` edge record and direct `frbroo:F1_Work -> frbroo:F1_Work` `frbroo:R2_is_derivative_of` triples emitted during RDF serialization while keeping `scripts/sync_ontology.py --check` green.

#### Scenario: OWL reasoner does not infer iqoqo:WorkRelation instances to be frbroo:F1_Work

- **GIVEN** `docs/ontology/iqoqo.ttl` loaded into an RDFS/OWL graph alongside an `iqoqo:WorkRelation` instance asserting `iqoqo:sourceWork <work/2>` and `iqoqo:targetWork <work/1>`
- **WHEN** RDFS domain entailment and `python scripts/sync_ontology.py --check` are evaluated
- **THEN** `iqoqo:sourceWork` has `rdfs:domain iqoqo:WorkRelation` and `rdfs:range frbroo:F1_Work` without `rdfs:subPropertyOf frbroo:R2_is_derivative_of`, the `iqoqo:WorkRelation` node is NOT entailed as `rdf:type frbroo:F1_Work`, and `scripts/sync_ontology.py --check` exits `0`
