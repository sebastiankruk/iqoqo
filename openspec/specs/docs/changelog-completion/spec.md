## Purpose

Ensures the CHANGELOG is complete and accurate for v0.8.0, following Keep a Changelog standards and providing users with clear information about all changes, features, fixes, and breaking changes in this release.

## Requirements

### Requirement: CHANGELOG has release date
The CHANGELOG SHALL have the actual release date for v0.8.0 instead of "TBD".

#### Scenario: Release date set

- **WHEN** user reads CHANGELOG
- **THEN** v0.8.0 entry has actual release date (not "TBD")

### Requirement: SPARQL endpoint documented
The CHANGELOG SHALL document the SPARQL query endpoint feature.

#### Scenario: SPARQL endpoint in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** SPARQL endpoint feature is listed under v0.8.0

### Requirement: Public Linked Data endpoints documented
The CHANGELOG SHALL document the public Linked Data endpoints feature.

#### Scenario: Public endpoints in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** public Linked Data endpoints are listed under v0.8.0

### Requirement: Schema.org SEO documented
The CHANGELOG SHALL document the Schema.org SEO mappings feature.

#### Scenario: Schema.org SEO in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** Schema.org SEO mappings are listed under v0.8.0

### Requirement: Data sovereignty export documented
The CHANGELOG SHALL document the data sovereignty export feature.

#### Scenario: Data export in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** data sovereignty export is listed under v0.8.0

### Requirement: Canonical IRI minting documented
The CHANGELOG SHALL document the canonical IRI minting feature.

#### Scenario: IRI minting in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** canonical IRI minting is listed under v0.8.0

### Requirement: FRBR ETL scripts documented
The CHANGELOG SHALL document the FRBR ETL scripts (safe and strict).

#### Scenario: ETL scripts in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** FRBR ETL scripts are listed under v0.8.0

### Requirement: Ontology synchronization documented
The CHANGELOG SHALL document the ontology synchronization feature.

#### Scenario: Ontology sync in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** ontology synchronization is listed under v0.8.0

### Requirement: Security fixes documented
The CHANGELOG SHALL document all security fixes including XSS prevention (#295).

#### Scenario: Security fixes in CHANGELOG

- **WHEN** user reads CHANGELOG
- **THEN** security fixes are listed under v0.8.0 with PR references

### Requirement: Breaking changes documented
The CHANGELOG SHALL clearly mark breaking changes (F3 column promotion).

#### Scenario: Breaking changes marked

- **WHEN** user reads CHANGELOG
- **THEN** breaking changes are clearly marked and explained
