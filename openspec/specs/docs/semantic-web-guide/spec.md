## Purpose

Provides comprehensive user-facing documentation for Semantic Web features, enabling users to understand and use SPARQL queries, public Linked Data endpoints, data export, Schema.org SEO, and IRI minting effectively.

## Requirements

### Requirement: Semantic Web guide document exists
The system SHALL have a Semantic Web guide at `docs/SEMANTIC_WEB.md` covering all Semantic Web features.

#### Scenario: Guide file exists

- **WHEN** user looks for Semantic Web documentation
- **THEN** `docs/SEMANTIC_WEB.md` exists and is accessible

### Requirement: SPARQL endpoint usage documented
The guide SHALL document how to use the SPARQL endpoint with examples.

#### Scenario: SPARQL usage documented

- **WHEN** user reads Semantic Web guide
- **THEN** guide explains SPARQL endpoint usage with query examples

### Requirement: Public Linked Data endpoints documented
The guide SHALL document public Linked Data endpoints and their usage.

#### Scenario: Public endpoints documented

- **WHEN** user reads Semantic Web guide
- **THEN** guide explains public endpoints (`/api/public/works/<id>`, etc.) with examples

### Requirement: Data export guide included
The guide SHALL include instructions for data sovereignty export.

#### Scenario: Data export documented

- **WHEN** user reads Semantic Web guide
- **THEN** guide explains how to export data in JSON-LD, Turtle, and JSON formats

### Requirement: Schema.org SEO explained
The guide SHALL explain Schema.org SEO benefits and how it works.

#### Scenario: Schema.org SEO documented

- **WHEN** user reads Semantic Web guide
- **THEN** guide explains Schema.org SEO mappings and their benefits

### Requirement: IRI minting configuration documented
The guide SHALL document IRI minting and BASE_URL configuration.

#### Scenario: IRI minting documented

- **WHEN** user reads Semantic Web guide
- **THEN** guide explains canonical IRI minting and how to configure BASE_URL

### Requirement: Content negotiation guide included
The guide SHALL include content negotiation documentation for RDF formats.

#### Scenario: Content negotiation documented

- **WHEN** user reads Semantic Web guide
- **THEN** guide explains content negotiation for JSON-LD, Turtle, N-Triples

### Requirement: AI agent integration examples
The guide SHALL include examples for AI agent integration with Linked Data.

#### Scenario: AI agent examples present

- **WHEN** user reads Semantic Web guide
- **THEN** guide provides examples for AI agents to consume Linked Data
