# frbr-ui-type-change Specification

## Purpose

TBD - created by archiving change frbr-ui-type-change. Update Purpose after archive.

## Requirements

### Requirement: Frontend Type Selector

The system SHALL display a type selection dropdown in the FRBR entity edit form (e.g., Manifestation editor).

#### Scenario: Editing Manifestation Type

- **WHEN** a user edits a Manifestation in the FRBR UI
- **THEN** the form includes a dropdown to select a different FRBR type (e.g., Movie, Book, Board Game)

### Requirement: Type Change Request Submission

The system SHALL route type changes made by non-admin users through the User Requests system.

#### Scenario: Submitting Type Change

- **WHEN** a regular user submits a type change for a Manifestation
- **THEN** the system creates a User Request of type `CHANGE_TYPE` and does not immediately update the entity

### Requirement: Custodian Type Change Approval

The system SHALL allow Custodians (admins) to approve and apply type changes via the Custodian UI, and this workflow SHALL be verified by automated End-to-End tests.

#### Scenario: Approving Type Change

- **WHEN** a Custodian approves a `CHANGE_TYPE` User Request
- **THEN** the system updates the underlying FRBR entity's `type` attribute and resolves the request
- **AND** Playwright E2E tests validate that the parent Work and Expression records correctly adapt their types to maintain hierarchy consistency.
