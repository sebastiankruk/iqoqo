## ADDED Requirements

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
