---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:49Z
---

## ADDED Requirements

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
