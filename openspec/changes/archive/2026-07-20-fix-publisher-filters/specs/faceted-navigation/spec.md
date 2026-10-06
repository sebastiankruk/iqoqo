---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## MODIFIED Requirements

### Requirement: Publisher facet filters records correctly

When a user filters by a Publisher value, the system MUST match against both the relational publisher column and any unstructured metadata fields (e.g., `meta['Publisher']`, `meta['publisher']`, and conditionally `meta['label']` for music releases). The system SHALL display records that match the publisher in any of these locations.

#### Scenario: Publisher facet matches relational column

- **WHEN** the user selects a Publisher value
- **AND** the matching publisher is stored in the `Manifestation.publisher` column
- **THEN** the backend SHALL return records associated with that publisher

#### Scenario: Publisher facet matches JSON metadata

- **WHEN** the user selects a Publisher value
- **AND** the matching publisher is stored only in the `Manifestation.meta['Publisher']` JSON field
- **THEN** the backend SHALL return records associated with that publisher

#### Scenario: Publisher faceted counts include JSON metadata

- **WHEN** the faceted sidebar generates `publisherCounts`
- **THEN** it SHALL include distinct publishers extracted and coalesced from both the relational column and the JSON `meta` fields.
