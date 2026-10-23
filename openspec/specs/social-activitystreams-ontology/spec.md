# social-activitystreams-ontology Specification

## Purpose
OWL and SHACL ontology extensions mapping collections, friends, wishlists, and custody loans to ActivityStreams 2.0 and CIDOC CRM.

## Requirements

### Requirement: Social Semantic Web Mapping

The system SHALL serialize social interactions using standard ActivityStreams 2.0 and CIDOC CRM ontologies.

#### Scenario: Custody loan serialized as CIDOC E10

- **WHEN** An Item custody event is exported to RDF
- **THEN** Emits crm:E10_Transfer_of_Custody and validates against iqoqo-shapes.ttl.
