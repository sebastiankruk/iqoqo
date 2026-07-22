# item-custody Specification

## Purpose

TBD - created by archiving change architectural-hardening-phase-2. Update Purpose after archive.

## Requirements

### Requirement: Immutable Item Custody Logging

The system SHALL maintain an append-only, immutable event log for all custody changes explicitly tied to the FRBR Item entity.

#### Scenario: Valid Item Custody Event

- **WHEN** an item's custody changes
- **THEN** the system logs a CIDOC CRM-compliant event to the `ItemCustodyEvent` table without modifying other entity tiers (Work, Expression, Manifestation).

### Requirement: Custody Loan Request Restrictions

The system SHALL ensure that loan request actions are only visible when the item is legally borrowable. Pure wishlist items (which are not owned or in custody of any user) MUST NOT display loan request options. Additionally, unauthenticated users SHALL NOT see loan request options, as they cannot initiate loans.

#### Scenario: Unauthenticated user views a borrowable item

- **WHEN** an unauthenticated viewer views a shared item that is normally borrowable
- **THEN** the system SHALL NOT render the "Request loan" button.

#### Scenario: Authenticated user views a wishlist item

- **WHEN** an authenticated user views an item that only exists as a wishlist entry (no physical custody)
- **THEN** the system SHALL NOT render the "Request loan" button.
