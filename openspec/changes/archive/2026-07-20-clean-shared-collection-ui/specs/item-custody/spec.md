---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## ADDED Requirements

### Requirement: Custody Loan Request Restrictions

The system SHALL ensure that loan request actions are only visible when the item is legally borrowable. Pure wishlist items (which are not owned or in custody of any user) MUST NOT display loan request options. Additionally, unauthenticated users SHALL NOT see loan request options, as they cannot initiate loans.

#### Scenario: Unauthenticated user views a borrowable item

- **WHEN** an unauthenticated viewer views a shared item that is normally borrowable
- **THEN** the system SHALL NOT render the "Request loan" button.

#### Scenario: Authenticated user views a wishlist item

- **WHEN** an authenticated user views an item that only exists as a wishlist entry (no physical custody)
- **THEN** the system SHALL NOT render the "Request loan" button.
