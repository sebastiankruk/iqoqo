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

### Requirement: Escalation Hook Visibility on Custody-Adjacent Views

The system SHALL surface escalation trigger hooks on custody-adjacent display views (item detail, manifestation detail) for authenticated users who lack elevated metadata write permissions. These hooks provide a structured path from the user's read-only view to the custodian's administrative queue without granting any direct write access to FRBR metadata.

#### Scenario: Non-custodian user views item detail with locked metadata

- **WHEN** an authenticated user without `write:metadata` permission views an item whose manifestation metadata fields (title, ISBN, format) are locked for editing
- **THEN** the system SHALL render an escalation trigger within the item actions panel, allowing the user to submit a change request to custodians.

#### Scenario: Non-custodian user views manifestation detail with locked metadata

- **WHEN** an authenticated user without `write:metadata` permission views a manifestation detail page where system-level metadata fields are not editable
- **THEN** the system SHALL render an escalation trigger within the manifestation actions section, allowing the user to submit a change request to custodians.

#### Scenario: Custodian or admin views item detail

- **WHEN** a user with `write:metadata` permission views an item detail page
- **THEN** the system SHALL NOT render the escalation trigger, because the user already has direct access to edit the metadata via the "Edit FRBR" admin action.

