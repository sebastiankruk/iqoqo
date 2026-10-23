# sparql-federated-access-rights Specification

## Purpose
Enforce privacy boundaries across SPARQL runner snapshots and public RDF exports, and record Fuseki evaluation ADR.

## Requirements

### Requirement: SPARQL Snapshot Privacy Scoping

The system SHALL exclude non-consented users and private items from unauthenticated SPARQL execution snapshots.

#### Scenario: Private item excluded from public SPARQL

- **WHEN** A public SPARQL query searches for all items
- **THEN** Items with is_public=False are omitted from the snapshot graph.
