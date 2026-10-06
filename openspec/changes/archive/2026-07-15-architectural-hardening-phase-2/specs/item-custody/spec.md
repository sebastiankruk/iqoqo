---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## ADDED Requirements

### Requirement: Immutable Item Custody Logging

The system SHALL maintain an append-only, immutable event log for all custody changes explicitly tied to the FRBR Item entity.

#### Scenario: Valid Item Custody Event

- **WHEN** an item's custody changes
- **THEN** the system logs a CIDOC CRM-compliant event to the `ItemCustodyEvent` table without modifying other entity tiers (Work, Expression, Manifestation).
