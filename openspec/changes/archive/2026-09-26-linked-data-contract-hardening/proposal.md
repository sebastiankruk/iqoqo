## Why

The semantic release has multiple representations of the same FRBR entities: public RDF and authenticated exports mint different IRIs, SHACL shapes and serializer namespaces are not fully aligned, and frontend Schema.org mapping ignores `expressionKind`. These inconsistencies reduce interoperability and make validation results misleading even when individual payloads parse.

## What Changes

- Define one canonical IRI policy and apply it consistently to models, public RDF, SPARQL graphs, exports, and JSON-LD.
- Align serializer namespaces/types with the OWL/SHACL contract, including contributor value shapes and custom-vocabulary relationships.
- Expand ontology synchronization checks beyond class-name presence to properties, domains/ranges, and required shapes; make CI fail on drift.
- Map `live_performance`/concert expressions consistently to Schema.org event semantics across backend and frontend.
- Add cross-format semantic contract tests that compare entity identity, required relationships, and SHACL conformance.

## Capabilities

### New Capabilities

### Modified Capabilities

- `semantic/ontology-sync`: Require property-level drift detection and an enforceable CI check.
- `semantic/rdf-serialization`: Require canonical IRIs, namespace alignment, and shape-compatible contributor relationships.
- `semantic/schema-org-seo`: Require expression-kind-aware Schema.org type mapping.

## Impact

- FRBR model IRI helpers, `app/core/frbr_service.py`, `app/core/export_service.py`, `scripts/sync_ontology.py`, ontology/SHACL files, frontend Schema.org mapping, and semantic tests.
- Consumers should receive stable identifiers; existing non-canonical URLs may need compatibility redirects or aliases.
