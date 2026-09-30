## ADDED Requirements

### Requirement: Safe Public Linked-Data Negotiation

Public semantic endpoints MUST apply one consistent content-negotiation and bounded-pagination policy across profile, shared-collection, Work, Expression, Manifestation, and Item representations.

#### Scenario: Equivalent Accept headers

- **WHEN** equivalent public RDF requests use the same supported Accept format
- **THEN** they receive the same media type, limit policy, and validity guarantees regardless of route

#### Scenario: Public sitemap generation

- **WHEN** a sitemap is requested for a large catalog
- **THEN** generation remains within documented bounds and uses cache/rate-limit controls without exposing private profile or expired-share URLs
