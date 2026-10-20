## Purpose
Peer instance Trust Graph, health probes, provenance tracking, and Custodian Provider Merge queue integration.

## ADDED Requirements

### Requirement: Trust-Gated Metadata Reconciliation

The system SHALL auto-merge metadata only from trusted peers and queue pending peer updates for custodian review.

#### Scenario: Trusted peer updates empty field
- **WHEN** A trusted peer sends an Update activity for a Manifestation with empty page_count
- **THEN** Local field is updated and meta['_provenance']['page_count'] records federation origin.

