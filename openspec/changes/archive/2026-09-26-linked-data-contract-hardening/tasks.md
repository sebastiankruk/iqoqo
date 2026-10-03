## 1. Canonical identity and namespaces

- [x] 1.1 Define canonical IRI routes and shared helpers for Work, Expression, Manifestation, and Item, and verify the policy fixture.
- [x] 1.2 Update public RDF, SPARQL graph, export serializers, and model helpers to use the same IRIs, and verify cross-format equality.
- [x] 1.3 Normalize FRBR/iqoqo class and relationship namespaces and update SHACL expectations, and verify enriched graph conformance.

## 2. Ontology and mapping gates

- [x] 2.1 Expand ontology sync to compare properties, domains, ranges, and required SHACL shapes, and verify intentional drift exits non-zero.
- [x] 2.2 Make the Makefile CI target pass strict check mode by default, and verify the target fails on a synthetic drift.
- [x] 2.3 Implement shared Expression-kind mapping and apply `live_performance` semantics in backend/frontend paths, and verify Schema.org event fixtures.

## 3. Cross-format verification

- [x] 3.1 Add enriched fixture coverage for contributors, parts, collections, image/provenance, and event metadata, and verify fixtures parse.
- [x] 3.2 Assert canonical IRI equality across JSON-LD, Turtle, N-Triples, public RDF, and SPARQL graphs, and verify no aliases appear unexpectedly.
- [x] 3.3 Validate enriched graphs with SHACL and run ontology, RDF, Schema.org, and frontend semantic test suites, recording successful results.
