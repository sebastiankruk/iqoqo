# semantic/ontology-sync Specification

## Purpose

Maintains OWL ontologies and SHACL shapes synchronized with the database schema, providing core validation services and canonical entity IRI minting for Linked Open Data.

## Requirements

### Requirement: Ground Truth OWL Ontology Synchronization

The system MUST maintain `docs/ontology/iqoqo.ttl` synchronized with the relational database schema, representing FRBR entities, catalog extensions, user intents, custody events, lending requests, reading roadmaps, social feedback, tags, and audit logging as valid OWL classes and properties.

#### Scenario: Verifying OWL class and property declarations

- **WHEN** the ontology is parsed and verified by automated tools
- **THEN** all post-v0.7.18 domain entities (`UserWorkIntent`, `ItemCustodyEvent`, `LoanRequest`, `ReadingRoadmap`, `RoadmapItem`, `Tag`, `ItemTag`, `SocialNote`, `EscalationRequest`, `EntityAuditLog`) have corresponding OWL class definitions with valid domain and range declarations.

### Requirement: Comprehensive SHACL Constraint Shapes

The system MUST maintain `docs/ontology/iqoqo-shapes.ttl` containing SHACL NodeShapes and PropertyShapes enforcing structural, cardinality, and type constraints across FRBR entities and domain models.

#### Scenario: SHACL validation of valid domain graph

- **WHEN** an RDF graph conforming to FRBR and domain entity constraints is validated against `docs/ontology/iqoqo-shapes.ttl`
- **THEN** the validation succeeds with `conforms=True` and produces no violation report entries.

#### Scenario: SHACL validation of invalid relationships

- **WHEN** an RDF graph contains invalid entity links (such as an expansion Work aggregated into a container Work or an Item lacking a manifestation reference)
- **THEN** the validation fails with `conforms=False` and reports the specific constraint violation.

### Requirement: Automated Ontology Sync Script with CI Check Mode

The system SHALL provide an operational script `scripts/sync_ontology.py` supporting a non-mutating `--check` mode that validates Turtle syntax and schema-to-ontology parity for CI pipelines.

#### Scenario: Running sync check in CI

- **WHEN** `python scripts/sync_ontology.py --check` is executed against valid, synchronized ontology and shapes files
- **THEN** the script exits with status code 0 and reports all ontology and shape checks passing.

#### Scenario: Running sync check on drifted or invalid ontology

- **WHEN** `python scripts/sync_ontology.py --check` is executed against an ontology file with syntax errors or missing required model entities
- **THEN** the script exits with a non-zero status code and prints diagnostic error details to stderr.

### Requirement: Centralized SHACL Validation Service

The system SHALL provide a core service module `app/core/shacl_service.py` offering `validate_graph()` and `validate_rdf_string()` functions that validate input RDF graphs or strings against the canonical SHACL shapes with RDFS inferencing.

#### Scenario: Validating in-memory RDF Graph

- **WHEN** a caller passes an `rdflib.Graph` to `validate_graph()`
- **THEN** the service executes SHACL validation against the canonical shapes graph and returns a tuple of `(conforms, results_graph, results_text)`.

#### Scenario: Validating serialized RDF string

- **WHEN** a caller passes a Turtle or JSON-LD formatted string to `validate_rdf_string()`
- **THEN** the service parses the string into an RDF graph, executes SHACL validation, and returns the conformity status and validation report.

### Requirement: Stable Entity IRI Minting on FRBR Models

The system SHALL provide a stable `iri` property on all core FRBR models (`Work`, `Expression`, `Manifestation`, `Item`) that produces a canonical URI for Linked Data `@id` generation.

#### Scenario: Resolving Work IRI

- **WHEN** the `iri` property of a Work with ID 42 is accessed
- **THEN** it returns `https://iqoqo.cc/works/42` (or the instance-configured base URL with `/works/42`).

#### Scenario: Resolving Expression, Manifestation, and Item IRIs

- **WHEN** the `iri` property of Expression 10, Manifestation 20, or Item 30 is accessed
- **THEN** it returns the respective canonical IRI (`/expressions/10`, `/manifestations/20`, `/items/30`).

### Requirement: Property-Level Ontology Drift Gate

Ontology synchronization checks MUST detect drift in mapped classes, properties, domains, ranges, and required SHACL coverage, and the CI-facing command MUST fail on detected drift or invalid syntax.

#### Scenario: Property or range removed

- **WHEN** a database-mapped ontology property, domain, or range is missing or changed
- **THEN** synchronization reports the drift and exits non-zero in check mode

#### Scenario: SHACL shape missing for required entity

- **WHEN** a required mapped entity has no corresponding required shape
- **THEN** synchronization reports the missing validation coverage and exits non-zero in check mode

#### Scenario: Clean synchronization

- **WHEN** model mappings, ontology declarations, and SHACL coverage match
- **THEN** the check exits zero with a diagnostic summary
