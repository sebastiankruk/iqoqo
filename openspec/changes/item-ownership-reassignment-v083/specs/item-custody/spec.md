## MODIFIED Requirements

### Requirement: Immutable Item Custody Logging

The system SHALL maintain an append-only, immutable event log for all custody changes explicitly tied to the FRBR Item entity. An ownership reassignment SHALL be recorded as a custody transfer with structured Item, previous-owner, new-owner, acting-user, and recorded-time values. Recording a transfer SHALL NOT modify or delete any earlier custody event.

#### Scenario: Valid Item Custody Event

- **WHEN** an item's custody changes
- **THEN** the system logs a CIDOC CRM-compliant event to the `ItemCustodyEvent` table without modifying other entity tiers (Work, Expression, Manifestation).

#### Scenario: Ownership reassignment is recorded as a transfer
- **WHEN** an authorized ownership-reassignment operation changes an Item owner
- **THEN** the system appends one immutable transfer event with structured previous and new owner identities, the acting user, and timestamp in the same transaction as the ownership change

#### Scenario: Transfer event persistence fails
- **WHEN** the system cannot append the custody event for an ownership reassignment
- **THEN** the ownership change and all other changes in that operation are rolled back
