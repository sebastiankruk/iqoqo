---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## ADDED Requirements

### Requirement: Contextual Wishlist Actions Visibility

The system SHALL ensure that wishlist management actions (such as removing an item from the wishlist via the quick-action toggle) are only accessible to the authenticated owner of the collection.

#### Scenario: Unauthenticated user views shared wishlist item

- **WHEN** an unauthenticated user views an item card for a wishlist item on a shared public page
- **THEN** the system SHALL NOT render the actionable removal toggle (Heart icon) or any duplicate state indicators.

#### Scenario: Authenticated user views their own wishlist item

- **WHEN** the authenticated owner views an item card for their own wishlist item
- **THEN** the system SHALL render the actionable removal toggle to allow quick deletion.
